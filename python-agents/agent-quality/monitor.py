"""实时缺陷监控模块。

聚合 AOI 缺陷率数据点，按阈值判定 OK/ALERT/INSUFFICIENT_DATA，
ALERT 时持久化到 quality_alerts 表。错误不在此模块捕获，
统一交由 main.py 异常处理器兜底。
"""

from datetime import datetime, timedelta, timezone

from shared.config import settings

from shared.device_client import device_client

from . import alert_store

# 监控的采集点编码（AOI 缺陷率）
_DATAPOINT_CODE = "AOI_DEFECT_RATE"


async def monitor(device_id: int) -> dict:
    """实时缺陷监控主流程。

    1. 计算时间窗口（最近 quality_monitor_window_hours 小时）
    2. 校验设备存在并取 AOI 缺陷率数据
    3. 数据为空 → INSUFFICIENT_DATA；否则计算均值并对比阈值
    4. 超阈值 → ALERT 并落库；否则 OK

    Args:
        device_id: 设备 ID。

    Returns:
        与 MonitorResponse 字段对齐的 dict。

    Raises:
        DeviceServiceUnavailable: device-service 不可达时透传给上层。
    """
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=settings.quality_monitor_window_hours)

    # 1. 校验设备存在（同时获取设备信息；DeviceServiceUnavailable 透传）
    await device_client.get_device(device_id)

    # 2. 取 AOI 缺陷率数据
    records = await device_client.get_device_data(
        device_id,
        _DATAPOINT_CODE,
        start_time.isoformat(),
        end_time.isoformat(),
    )

    analyzed_at = datetime.now(timezone.utc).isoformat()
    threshold = settings.quality_aoi_defect_rate_threshold

    if not records:
        return {
            "device_id": device_id,
            "defect_rate": 0.0,
            "threshold": threshold,
            "status": "INSUFFICIENT_DATA",
            "datapoints": [],
            "analyzed_at": analyzed_at,
        }

    # 3. 解析数据点：跳过 value/timestamp 缺失或无法解析的记录
    datapoints: list[dict] = []
    values: list[float] = []
    for rec in records:
        raw_value = rec.get("value")
        ts = rec.get("timestamp")
        if raw_value is None or ts is None:
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        values.append(value)
        datapoints.append(
            {
                "datapoint_code": _DATAPOINT_CODE,
                "value": value,
                "timestamp": str(ts),
            }
        )

    if not values:
        return {
            "device_id": device_id,
            "defect_rate": 0.0,
            "threshold": threshold,
            "status": "INSUFFICIENT_DATA",
            "datapoints": [],
            "analyzed_at": analyzed_at,
        }

    # 4. 计算均值并判定
    defect_rate = sum(values) / len(values)

    if defect_rate > threshold:
        status = "ALERT"
        await alert_store.save_alert(
            device_id=device_id,
            defect_rate=defect_rate,
            threshold=threshold,
            status=status,
            datapoint_code=_DATAPOINT_CODE,
        )
    else:
        status = "OK"

    return {
        "device_id": device_id,
        "defect_rate": defect_rate,
        "threshold": threshold,
        "status": status,
        "datapoints": datapoints,
        "analyzed_at": analyzed_at,
    }
