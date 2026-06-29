"""agent_maintenance.predict 单元测试。

使用 monkeypatch 替换 predict 模块内的 device_client 引用，
不触达真实 Java device-service。

P0 B1：predict.predict 已改 async，device_client 三方法已改 async，
测试同步改 async def + AsyncMock。
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_maintenance.device_client import DeviceServiceUnavailable
from agent_maintenance.predict import predict


def _make_record(idx: int, code: str, value: float, ts: datetime) -> dict:
    """构造一条采集数据记录。"""
    return {
        "id": idx,
        "deviceId": 1,
        "datapointCode": code,
        "value": str(value),
        "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


async def test_predict_data_insufficient(monkeypatch):
    """数据时间跨度不足 24 小时应返回 data_sufficient=False。"""
    mock_device = MagicMock()
    mock_device.get_device = AsyncMock(return_value={"id": 1, "deviceName": "贴片机"})
    mock_device.list_datapoints = AsyncMock(
        return_value=[
            {
                "id": 1,
                "deviceId": 1,
                "datapointCode": "TEMP-01",
                "datapointName": "温度",
                "nodePath": "/temp",
                "dataType": "NUMBER",
                "sampleIntervalMs": 60000,
            }
        ]
    )
    # 3 条数据，跨度 2 小时（< 24h）
    base = datetime(2026, 6, 28, 0, 0, 0, tzinfo=timezone.utc)
    records = [
        _make_record(0, "TEMP-01", 70.0, base),
        _make_record(1, "TEMP-01", 71.0, base + timedelta(hours=1)),
        _make_record(2, "TEMP-01", 72.0, base + timedelta(hours=2)),
    ]
    mock_device.get_device_data = AsyncMock(return_value=records)
    monkeypatch.setattr("agent_maintenance.predict.device_client", mock_device)

    result = await predict(1)

    assert result["data_sufficient"] is False
    assert result["trend"] == "数据不足"
    assert result["recommendation"] == "数据不足，无法预测"
    assert result["threshold_alerts"] == []
    assert result["forecast"] is None


async def test_predict_with_trend(monkeypatch):
    """7 天温度数据呈上升趋势应返回 trend=上升 并产生告警或预测。"""
    mock_device = MagicMock()
    mock_device.get_device = AsyncMock(return_value={"id": 1, "deviceName": "贴片机"})
    mock_device.list_datapoints = AsyncMock(
        return_value=[
            {
                "id": 1,
                "deviceId": 1,
                "datapointCode": "TEMP-01",
                "datapointName": "温度",
                "nodePath": "/temp",
                "dataType": "NUMBER",
                "sampleIntervalMs": 86400000,
            }
        ]
    )
    # 7 条数据，每天一条，跨度 6 天（>= 24h），值递增 70→82
    base = datetime(2026, 6, 21, 0, 0, 0, tzinfo=timezone.utc)
    records = [
        _make_record(i, "TEMP-01", 70.0 + i * 2, base + timedelta(days=i))
        for i in range(7)
    ]
    mock_device.get_device_data = AsyncMock(return_value=records)
    monkeypatch.setattr("agent_maintenance.predict.device_client", mock_device)

    result = await predict(1)

    assert result["data_sufficient"] is True
    assert result["trend"] == "上升"
    # 温度均值接近上限 80，应产生告警或预测
    assert len(result["threshold_alerts"]) > 0 or result["forecast"] is not None
    # 验证告警结构
    for alert in result["threshold_alerts"]:
        assert alert["datapoint_code"] == "TEMP-01"
        assert alert["severity"] in ("HIGH", "MEDIUM", "LOW")
        assert alert["threshold"] == 80.0


async def test_predict_device_unavailable(monkeypatch):
    """device-service 不可达时应抛出 DeviceServiceUnavailable。"""
    mock_device = MagicMock()
    mock_device.get_device = AsyncMock(side_effect=DeviceServiceUnavailable("connection refused"))
    monkeypatch.setattr("agent_maintenance.predict.device_client", mock_device)

    with pytest.raises(DeviceServiceUnavailable):
        await predict(1)


def _make_datapoint(code: str = "TEMP-01") -> dict:
    """构造一个 NUMBER 类型采集点配置。"""
    return {
        "id": 1,
        "deviceId": 1,
        "datapointCode": code,
        "datapointName": "温度",
        "nodePath": "/temp",
        "dataType": "NUMBER",
        "sampleIntervalMs": 86400000,
    }


def _make_seven_day_records(values: list[float], code: str = "TEMP-01") -> list[dict]:
    """根据值列表构造 7 天跨度（每天一个点）的采集数据记录。"""
    base = datetime(2026, 6, 21, 0, 0, 0, tzinfo=timezone.utc)
    return [
        _make_record(i, code, v, base + timedelta(days=i))
        for i, v in enumerate(values)
    ]


async def test_predict_decreasing_trend(monkeypatch):
    """值递减时应返回 trend=下降。补齐 phase2 B-5 盲区。"""
    mock_device = MagicMock()
    mock_device.get_device = AsyncMock(return_value={"id": 1, "deviceName": "贴片机"})
    mock_device.list_datapoints = AsyncMock(return_value=[_make_datapoint()])
    mock_device.get_device_data = AsyncMock(
        return_value=_make_seven_day_records([76.0, 75.0, 74.0, 73.0, 72.0, 71.0, 70.0])
    )
    monkeypatch.setattr("agent_maintenance.predict.device_client", mock_device)

    result = await predict(1)

    assert result["data_sufficient"] is True
    assert result["trend"] == "下降"


async def test_predict_stable_trend(monkeypatch):
    """值恒定时应返回 trend=平稳。"""
    mock_device = MagicMock()
    mock_device.get_device = AsyncMock(return_value={"id": 1, "deviceName": "贴片机"})
    mock_device.list_datapoints = AsyncMock(return_value=[_make_datapoint()])
    mock_device.get_device_data = AsyncMock(
        return_value=_make_seven_day_records([73.0] * 7)
    )
    monkeypatch.setattr("agent_maintenance.predict.device_client", mock_device)

    result = await predict(1)

    assert result["data_sufficient"] is True
    assert result["trend"] == "平稳"


async def test_predict_forecast_hours_to_threshold(monkeypatch):
    """构造已知斜率数据，验证 forecast.hours_to_threshold 数值计算。

    数据：7 个点，每天 +1（70→76），slope=1.0，sample_interval=24h。
    current_mean=73，TEMP max=80。
    hours_to_threshold = (80-73)/1.0 * 24 = 168 小时。
    """
    mock_device = MagicMock()
    mock_device.get_device = AsyncMock(return_value={"id": 1, "deviceName": "贴片机"})
    mock_device.list_datapoints = AsyncMock(return_value=[_make_datapoint()])
    mock_device.get_device_data = AsyncMock(
        return_value=_make_seven_day_records([70.0, 71.0, 72.0, 73.0, 74.0, 75.0, 76.0])
    )
    monkeypatch.setattr("agent_maintenance.predict.device_client", mock_device)

    result = await predict(1)

    assert result["data_sufficient"] is True
    assert result["forecast"] is not None
    assert result["forecast"]["datapoint_code"] == "TEMP-01"
    assert result["forecast"]["predicted_value"] == 80.0
    # hours_to_threshold = (80-73)/1.0 * 24 = 168，允许浮点误差
    assert abs(result["forecast"]["hours_to_threshold"] - 168.0) < 1.0
