"""agent_maintenance.predict 单元测试。

使用 monkeypatch 替换 predict 模块内的 device_client 引用，
不触达真实 Java device-service。
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

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


def test_predict_data_insufficient(monkeypatch):
    """数据时间跨度不足 24 小时应返回 data_sufficient=False。"""
    mock_device = MagicMock()
    mock_device.get_device.return_value = {"id": 1, "deviceName": "贴片机"}
    mock_device.list_datapoints.return_value = [
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
    # 3 条数据，跨度 2 小时（< 24h）
    base = datetime(2026, 6, 28, 0, 0, 0, tzinfo=timezone.utc)
    records = [
        _make_record(0, "TEMP-01", 70.0, base),
        _make_record(1, "TEMP-01", 71.0, base + timedelta(hours=1)),
        _make_record(2, "TEMP-01", 72.0, base + timedelta(hours=2)),
    ]
    mock_device.get_device_data.return_value = records
    monkeypatch.setattr("agent_maintenance.predict.device_client", mock_device)

    result = predict(1)

    assert result["data_sufficient"] is False
    assert result["trend"] == "数据不足"
    assert result["recommendation"] == "数据不足，无法预测"
    assert result["threshold_alerts"] == []
    assert result["forecast"] is None


def test_predict_with_trend(monkeypatch):
    """7 天温度数据呈上升趋势应返回 trend=上升 并产生告警或预测。"""
    mock_device = MagicMock()
    mock_device.get_device.return_value = {"id": 1, "deviceName": "贴片机"}
    mock_device.list_datapoints.return_value = [
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
    # 7 条数据，每天一条，跨度 6 天（>= 24h），值递增 70→82
    base = datetime(2026, 6, 21, 0, 0, 0, tzinfo=timezone.utc)
    records = [
        _make_record(i, "TEMP-01", 70.0 + i * 2, base + timedelta(days=i))
        for i in range(7)
    ]
    mock_device.get_device_data.return_value = records
    monkeypatch.setattr("agent_maintenance.predict.device_client", mock_device)

    result = predict(1)

    assert result["data_sufficient"] is True
    assert result["trend"] == "上升"
    # 温度均值接近上限 80，应产生告警或预测
    assert len(result["threshold_alerts"]) > 0 or result["forecast"] is not None
    # 验证告警结构
    for alert in result["threshold_alerts"]:
        assert alert["datapoint_code"] == "TEMP-01"
        assert alert["severity"] in ("HIGH", "MEDIUM", "LOW")
        assert alert["threshold"] == 80.0


def test_predict_device_unavailable(monkeypatch):
    """device-service 不可达时应抛出 DeviceServiceUnavailable。"""
    mock_device = MagicMock()
    mock_device.get_device.side_effect = DeviceServiceUnavailable("connection refused")
    monkeypatch.setattr("agent_maintenance.predict.device_client", mock_device)

    with pytest.raises(DeviceServiceUnavailable):
        predict(1)
