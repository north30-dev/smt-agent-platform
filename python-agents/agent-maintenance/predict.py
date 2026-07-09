"""预测性维护 v1 模块。

基于近 7 天采集点历史数据，计算滑动均值、阈值告警与简单线性外推，
给出整体趋势与运维建议。错误不在本模块捕获，统一交由 main.py 异常处理器兜底。
"""

from datetime import datetime, timedelta, timezone

from shared.config import settings

from shared.device_client import DeviceServiceUnavailable, device_client


async def predict(device_id: int) -> dict:
    """预测性维护主流程。

    1. 获取设备信息与采集点列表
    2. 对每个 NUMBER 类型采集点取近 7 天数据
    3. 计算滑动均值、阈值告警、简单线性外推
    4. 聚合趋势与最紧急预测项

    Args:
        device_id: 设备 ID。

    Returns:
        {trend, threshold_alerts, forecast, recommendation, data_sufficient}
    """
    # 1. 获取设备信息（同时验证设备存在）
    await device_client.get_device(device_id)

    # 2. 获取采集点列表
    datapoints = await device_client.list_datapoints(device_id)
    number_points = [
        dp for dp in datapoints if str(dp.get("dataType", "")).upper() == "NUMBER"
    ]

    if not number_points:
        return _insufficient_result()

    # 3. 取近 7 天数据
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=7)
    start_time = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    threshold_alerts: list[dict] = []
    forecast_candidates: list[dict] = []
    slopes: list[float] = []
    has_sufficient = False

    for dp in number_points:
        code = dp.get("datapointCode") or ""
        if not code:
            continue
        records = await device_client.get_device_data(
            device_id, code, start_time, end_time
        )
        points = _parse_points(records)
        if len(points) < 2:
            continue

        # 时间跨度判断
        times = [p[0] for p in points]
        span_hours = (max(times) - min(times)).total_seconds() / 3600.0
        if span_hours < settings.predict_min_span_hours:
            continue
        has_sufficient = True

        # 滑动窗口
        window_size = settings.predict_window_size
        window = points[-window_size:] if len(points) > window_size else points
        values = [p[1] for p in window]
        current_mean = sum(values) / len(values)

        # 斜率（最小二乘）
        slope = _linear_slope(values)
        slopes.append(slope)

        # 阈值告警
        threshold_cfg = _get_threshold(code)
        alert = _build_alert(code, current_mean, threshold_cfg)
        if alert is not None:
            threshold_alerts.append(alert)

        # 外推预测
        sample_interval_hours = _avg_interval_hours(window)
        forecast = _build_forecast(
            code, current_mean, slope, threshold_cfg, sample_interval_hours
        )
        if forecast is not None:
            forecast_candidates.append(forecast)

    if not has_sufficient:
        return _insufficient_result()

    # 4. 聚合结果
    trend = _aggregate_trend(slopes)
    forecast = _pick_most_urgent(forecast_candidates)
    recommendation = _build_recommendation(threshold_alerts)

    return {
        "trend": trend,
        "threshold_alerts": threshold_alerts,
        "forecast": forecast,
        "recommendation": recommendation,
        "data_sufficient": True,
    }


def _parse_points(records: list[dict]) -> list[tuple[datetime, float]]:
    """将原始 records 解析为 [(datetime, float)]，跳过无效点。"""
    points: list[tuple[datetime, float]] = []
    for rec in records:
        ts = rec.get("timestamp")
        raw_value = rec.get("value")
        if ts is None or raw_value is None:
            continue
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        try:
            value = float(raw_value)
        except (ValueError, TypeError):
            continue
        points.append((dt, value))
    return points


def _linear_slope(values: list[float]) -> float:
    """手写最小二乘法计算斜率，x 用索引 0..N-1。"""
    n = len(values)
    if n < 2:
        return 0.0
    xm = (n - 1) / 2.0
    ym = sum(values) / n
    num = 0.0
    den = 0.0
    for i, y in enumerate(values):
        num += (i - xm) * (y - ym)
        den += (i - xm) ** 2
    if den == 0:
        return 0.0
    return num / den


def _get_threshold(datapoint_code: str) -> dict:
    """根据 datapoint_code 前缀匹配阈值，无匹配用 DEFAULT。"""
    prefix = datapoint_code.split("-")[0].split("_")[0].upper()
    thresholds = settings.predict_thresholds
    return thresholds.get(prefix, thresholds["DEFAULT"])


def _build_alert(code: str, current_mean: float, cfg: dict) -> dict | None:
    """根据当前均值与阈值生成告警，无告警返回 None。"""
    max_v = cfg["max"]
    min_v = cfg["min"]

    # 上限告警
    if current_mean >= max_v:
        severity = "HIGH"
    elif current_mean >= max_v * 0.9:
        severity = "MEDIUM"
    elif current_mean >= max_v * 0.8:
        severity = "LOW"
    elif min_v > 0 and current_mean <= min_v:
        severity = "HIGH"
    elif min_v > 0 and current_mean <= min_v * 1.1:
        severity = "MEDIUM"
    elif min_v > 0 and current_mean <= min_v * 1.2:
        severity = "LOW"
    else:
        return None

    # threshold 取触发的那个边界
    if current_mean >= max_v * 0.8:
        threshold = max_v
    else:
        threshold = min_v

    return {
        "datapoint_code": code,
        "current_value": current_mean,
        "threshold": threshold,
        "severity": severity,
    }


def _build_forecast(
    code: str,
    current_mean: float,
    slope: float,
    cfg: dict,
    sample_interval_hours: float,
) -> dict | None:
    """根据斜率外推到阈值，生成预测项。无法估算返回 None。"""
    if slope <= 0 or sample_interval_hours <= 0:
        return None

    max_v = cfg["max"]
    # 选择更先到达的阈值边界（仅考虑上限，因为 slope > 0 时趋向上限）
    if current_mean >= max_v:
        hours_to_threshold = 0.0
    else:
        hours_to_threshold = (max_v - current_mean) / slope * sample_interval_hours
        if hours_to_threshold < 0:
            hours_to_threshold = 0.0

    return {
        "datapoint_code": code,
        "predicted_value": max_v,
        "hours_to_threshold": hours_to_threshold,
    }


def _avg_interval_hours(points: list[tuple[datetime, float]]) -> float:
    """估算数据点平均间隔（小时）。"""
    if len(points) < 2:
        return 0.0
    times = [p[0] for p in points]
    total = (max(times) - min(times)).total_seconds()
    return total / 3600.0 / (len(points) - 1)


def _aggregate_trend(slopes: list[float]) -> str:
    """根据各采集点斜率聚合整体趋势。"""
    if not slopes:
        return "平稳"
    avg = sum(slopes) / len(slopes)
    trend_threshold = settings.predict_trend_threshold
    if avg > trend_threshold:
        return "上升"
    if avg < -trend_threshold:
        return "下降"
    return "平稳"


def _pick_most_urgent(candidates: list[dict]) -> dict | None:
    """从预测候选中选出 hours_to_threshold 最小（最紧急）的。"""
    if not candidates:
        return None
    return min(candidates, key=lambda c: c["hours_to_threshold"])


def _build_recommendation(alerts: list[dict]) -> str:
    """根据告警严重程度生成运维建议。"""
    severities = {a["severity"] for a in alerts}
    if "HIGH" in severities:
        return "建议立即停机检查"
    if "MEDIUM" in severities:
        return "建议安排预防性维护"
    return "继续监控"


def _insufficient_result() -> dict:
    """数据不足时的兜底响应。"""
    return {
        "trend": "数据不足",
        "threshold_alerts": [],
        "forecast": None,
        "recommendation": "数据不足，无法预测",
        "data_sufficient": False,
    }
