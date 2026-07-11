# agent-maintenance/predict

> 预测性维护模块，基于近 7 天历史数据计算滑动均值、阈值告警与线性外推。

**模块路径**: `agent-maintenance/predict.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-maintenance/predict.py`

---

## 顶层函数

### `async predict(device_id: int) -> dict`

> 预测性维护分析

**签名**: `async def predict(device_id: int) -> dict`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `device_id` | `int` | 是 | 设备 ID |

**返回值**: `dict` — `{trend, threshold_alerts, forecast, recommendation, data_sufficient}`

**逻辑**:
1. 验证设备存在
2. 列出采集点，过滤 NUMBER 类型
3. 获取每个采集点最近 7 天数据
4. 计算滑动窗口均值、线性斜率、阈值告警、预测
5. 聚合趋势，选择最紧急的预测

---

### `_linear_slope(values: list[float]) -> float`

> 最小二乘法计算线性斜率

**签名**: `def _linear_slope(values: list[float]) -> float`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `values` | `list[float]` | 数值列表 |

**返回值**: `float` — 斜率值

---

### `_get_threshold(datapoint_code: str) -> dict`

> 获取采集点阈值配置

**签名**: `def _get_threshold(datapoint_code: str) -> dict`

**返回值**: `dict` — `{max, high, low, unit}`

---

### `_build_alert(code: str, current_mean: float, cfg: dict) -> dict | None`

> 构建阈值告警

**签名**: `def _build_alert(code: str, current_mean: float, cfg: dict) -> dict | None`

**返回值**: `dict | None` — `{datapoint_code, current_value, threshold, severity}`，无告警返回 None

**告警级别**:
- HIGH: 超过 max 阈值
- MEDIUM: 超过 high 阈值
- LOW: 超过 low 阈值

---

### `_build_forecast(code: str, current_mean: float, slope: float, cfg: dict, sample_interval_hours: float) -> dict | None`

> 构建趋势预测

**签名**: `def _build_forecast(code: str, current_mean: float, slope: float, cfg: dict, sample_interval_hours: float) -> dict | None`

**返回值**: `dict | None` — `{datapoint_code, predicted_value, hours_to_threshold}`

**逻辑**: 斜率 > 0 时外推到达阈值的时间

---

### `_aggregate_trend(slopes: list[float]) -> str`

> 聚合趋势判断

**签名**: `def _aggregate_trend(slopes: list[float]) -> str`

**返回值**: `str` — "上升" / "下降" / "平稳"

---

### `_build_recommendation(alerts: list[dict]) -> str`

> 生成运维建议

**签名**: `def _build_recommendation(alerts: list[dict]) -> str`

**返回值**: `str` — 基于告警级别的建议文本

**建议规则**:
- HIGH: 立即停机检修
- MEDIUM: 加强监控，预防性维护
- 其他: 继续监控
