"""agent_quality.monitor 单元测试。

使用 monkeypatch 替换 monitor 模块内已 import 的 device_client 引用与
alert_store.save_alert，不触达真实 Java device-service 与 PostgreSQL。

P0 B1：monitor.monitor 已改 async，device_client 三方法已改 async，
测试同步改 async def + AsyncMock。
- device_client.get_device/get_device_data → AsyncMock（被 await 调用）
- alert_store.save_alert → AsyncMock（被 await 调用）
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_quality import alert_store, monitor
from shared.device_client import DeviceServiceUnavailable


@pytest.fixture(autouse=True)
def _reset_alert_pool():
    """每个用例前后重置 alert_store 模块级连接池，避免跨用例污染。"""
    alert_store._pool = None
    yield
    alert_store._pool = None


def _make_record(idx: int, value: float, ts: datetime) -> dict:
    """构造一条 AOI 缺陷率记录。

    与 device-service 返回结构对齐：value 字段为字符串，
    timestamp 为 ISO 字符串（参考 agent_maintenance.predict._make_record）。
    """
    return {
        "id": idx,
        "deviceId": 1,
        "datapointCode": "AOI_DEFECT_RATE",
        "value": str(value),
        "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _patch_device_client(
    monkeypatch,
    *,
    device_return=None,
    device_side_effect=None,
    data_return=None,
    data_side_effect=None,
):
    """辅助：mock monitor 模块的 device_client 引用。

    device_client.get_device / get_device_data 为 AsyncMock。
    """
    mock_device = MagicMock()
    if device_side_effect is not None:
        mock_device.get_device = AsyncMock(side_effect=device_side_effect)
    else:
        mock_device.get_device = AsyncMock(
            return_value=device_return
            if device_return is not None
            else {"id": 1, "deviceName": "贴片机"}
        )
    if data_side_effect is not None:
        mock_device.get_device_data = AsyncMock(side_effect=data_side_effect)
    else:
        mock_device.get_device_data = AsyncMock(
            return_value=data_return if data_return is not None else []
        )
    monkeypatch.setattr("agent_quality.monitor.device_client", mock_device)
    return mock_device


async def test_monitor_normal_ok(monkeypatch):
    """缺陷率均值低于阈值应返回 status=OK，不写告警。"""
    base = datetime(2026, 7, 6, 0, 0, 0, tzinfo=timezone.utc)
    records = [
        _make_record(0, 0.005, base),
        _make_record(1, 0.008, base + timedelta(minutes=10)),
        _make_record(2, 0.006, base + timedelta(minutes=20)),
    ]
    _patch_device_client(monkeypatch, data_return=records)

    save_alert_mock = AsyncMock(return_value=1)
    monkeypatch.setattr("agent_quality.monitor.alert_store.save_alert", save_alert_mock)

    result = await monitor.monitor(1)

    assert result["device_id"] == 1
    assert result["status"] == "OK"
    # 均值 (0.005+0.008+0.006)/3 ≈ 0.00633
    assert abs(result["defect_rate"] - 0.00633) < 0.0001
    assert result["threshold"] == 0.02  # settings.quality_aoi_defect_rate_threshold
    assert len(result["datapoints"]) == 3
    assert result["datapoints"][0]["datapoint_code"] == "AOI_DEFECT_RATE"
    assert result["datapoints"][0]["value"] == 0.005
    assert result["analyzed_at"]
    save_alert_mock.assert_not_called()


async def test_monitor_alert_persists(monkeypatch):
    """缺陷率均值高于阈值应返回 status=ALERT 并写一条告警。"""
    base = datetime(2026, 7, 6, 0, 0, 0, tzinfo=timezone.utc)
    records = [
        _make_record(0, 0.05, base),
        _make_record(1, 0.04, base + timedelta(minutes=10)),
    ]
    _patch_device_client(monkeypatch, data_return=records)

    save_alert_mock = AsyncMock(return_value=42)
    monkeypatch.setattr("agent_quality.monitor.alert_store.save_alert", save_alert_mock)

    result = await monitor.monitor(1)

    assert result["status"] == "ALERT"
    # 均值 (0.05+0.04)/2 = 0.045
    assert abs(result["defect_rate"] - 0.045) < 0.0001
    assert result["threshold"] == 0.02
    assert len(result["datapoints"]) == 2

    save_alert_mock.assert_called_once()
    kwargs = save_alert_mock.call_args.kwargs
    assert kwargs["device_id"] == 1
    assert kwargs["status"] == "ALERT"
    assert kwargs["datapoint_code"] == "AOI_DEFECT_RATE"
    assert abs(kwargs["defect_rate"] - 0.045) < 0.0001
    assert kwargs["threshold"] == 0.02


async def test_monitor_threshold_boundary_not_alert(monkeypatch):
    """缺陷率均值恰好等于阈值时不应触发 ALERT（严格 > 才告警）。"""
    base = datetime(2026, 7, 6, 0, 0, 0, tzinfo=timezone.utc)
    records = [
        _make_record(0, 0.02, base),
        _make_record(1, 0.02, base + timedelta(minutes=10)),
    ]
    _patch_device_client(monkeypatch, data_return=records)

    save_alert_mock = AsyncMock(return_value=1)
    monkeypatch.setattr("agent_quality.monitor.alert_store.save_alert", save_alert_mock)

    result = await monitor.monitor(1)

    assert result["status"] == "OK"
    assert abs(result["defect_rate"] - 0.02) < 0.0001
    save_alert_mock.assert_not_called()


async def test_monitor_insufficient_data_empty_records(monkeypatch):
    """无数据记录时应返回 status=INSUFFICIENT_DATA。"""
    _patch_device_client(monkeypatch, data_return=[])

    save_alert_mock = AsyncMock()
    monkeypatch.setattr("agent_quality.monitor.alert_store.save_alert", save_alert_mock)

    result = await monitor.monitor(1)

    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["defect_rate"] == 0.0
    assert result["datapoints"] == []
    assert result["threshold"] == 0.02
    save_alert_mock.assert_not_called()


async def test_monitor_insufficient_data_all_invalid_values(monkeypatch):
    """全部记录 value 无法解析时应返回 INSUFFICIENT_DATA。"""
    records = [
        {"value": None, "timestamp": "2026-07-06T00:00:00Z"},
        {"value": "not-a-number", "timestamp": "2026-07-06T00:10:00Z"},
        {"value": "0.01", "timestamp": None},  # timestamp 缺失也跳过
    ]
    _patch_device_client(monkeypatch, data_return=records)

    save_alert_mock = AsyncMock()
    monkeypatch.setattr("agent_quality.monitor.alert_store.save_alert", save_alert_mock)

    result = await monitor.monitor(1)

    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["datapoints"] == []
    save_alert_mock.assert_not_called()


async def test_monitor_partial_invalid_records(monkeypatch):
    """部分记录无效时应跳过无效项，仅对有效项计算均值。"""
    base = datetime(2026, 7, 6, 0, 0, 0, tzinfo=timezone.utc)
    records = [
        _make_record(0, 0.005, base),
        {"value": None, "timestamp": "2026-07-06T00:10:00Z"},  # 跳过
        _make_record(2, 0.007, base + timedelta(minutes=20)),
    ]
    _patch_device_client(monkeypatch, data_return=records)

    monkeypatch.setattr(
        "agent_quality.monitor.alert_store.save_alert", AsyncMock(return_value=1)
    )

    result = await monitor.monitor(1)

    assert result["status"] == "OK"
    # 仅 2 条有效：均值 (0.005+0.007)/2 = 0.006
    assert abs(result["defect_rate"] - 0.006) < 0.0001
    assert len(result["datapoints"]) == 2


async def test_monitor_device_unavailable(monkeypatch):
    """device-service 不可达时应抛出 DeviceServiceUnavailable。"""
    _patch_device_client(
        monkeypatch,
        device_side_effect=DeviceServiceUnavailable("connection refused"),
    )

    with pytest.raises(DeviceServiceUnavailable):
        await monitor.monitor(1)


async def test_monitor_calls_get_device_for_validation(monkeypatch):
    """monitor 应先调用 get_device 校验设备存在。"""
    base = datetime(2026, 7, 6, 0, 0, 0, tzinfo=timezone.utc)
    records = [_make_record(0, 0.005, base)]
    mock_device = _patch_device_client(monkeypatch, data_return=records)
    monkeypatch.setattr(
        "agent_quality.monitor.alert_store.save_alert", AsyncMock(return_value=1)
    )

    await monitor.monitor(42)

    mock_device.get_device.assert_called_once_with(42)
    mock_device.get_device_data.assert_called_once()
    # 调用 get_device_data 时采集点编码应为 AOI_DEFECT_RATE
    args = mock_device.get_device_data.call_args.args
    assert args[0] == 42
    assert args[1] == "AOI_DEFECT_RATE"
