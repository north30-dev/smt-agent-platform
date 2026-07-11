# agent-quality/monitor

> 实时缺陷监控模块，聚合 AOI 缺陷率数据点，按阈值判定状态。

**模块路径**: `agent-quality/monitor.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-quality/monitor.py`

---

## 模块级常量

| 名称 | 类型 | 说明 |
|------|------|------|
| `_DATAPOINT_CODE` | `str` | `"AOI_DEFECT_RATE"` |

---

## 顶层函数

### `async monitor(device_id: int) -> dict`

> 执行缺陷监控分析

**签名**: `async def monitor(device_id: int) -> dict`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `device_id` | `int` | 是 | 设备 ID |

**返回值**: `dict` — `{device_id, defect_rate, threshold, status, datapoints, analyzed_at}`

**状态判定**:
- `OK`: 缺陷率 ≤ 阈值
- `ALERT`: 缺陷率 > 阈值（同时持久化到 quality_alerts 表）
- `INSUFFICIENT_DATA`: 无数据

**逻辑**:
1. 计算时间窗口（最近 N 小时）
2. 验证设备存在
3. 获取 AOI 缺陷率数据
4. 空数据 → INSUFFICIENT_DATA
5. 计算均值 → 与阈值比较
6. 超阈值 → ALERT + 持久化告警
