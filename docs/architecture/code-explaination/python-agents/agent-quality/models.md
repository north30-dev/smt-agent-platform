# agent-quality/models

> 质量分析 Agent 的 Pydantic 请求/响应模型。

**模块路径**: `agent-quality/models.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-quality/models.py`

---

## 类

### `MonitorResponse(BaseModel)`

| 字段 | 类型 | 说明 |
|------|------|------|
| `device_id` | `int` | 设备 ID |
| `defect_rate` | `float` | 缺陷率 |
| `threshold` | `float` | 阈值 |
| `status` | `str` | 状态（OK/ALERT/INSUFFICIENT_DATA） |
| `datapoints` | `list[MonitorDatapoint]` | 数据点列表 |
| `analyzed_at` | `str` | 分析时间 |

### `RootCauseRequest(BaseModel)`

| 字段 | 类型 | 校验 | 说明 |
|------|------|------|------|
| `device_id` | `int` | `ge=1` | 设备 ID |
| `defect_description` | `str` | `min_length=1, max_length=2000` | 缺陷描述 |

### `RootCause(BaseModel)`

| 字段 | 类型 | 说明 |
|------|------|------|
| `category` | `str` | 因素类别（人/机/料/法/环） |
| `cause` | `str` | 具体原因 |

### `RootCauseResponse(BaseModel)`

| 字段 | 类型 | 说明 |
|------|------|------|
| `device_id` | `int` | 设备 ID |
| `root_causes` | `list[RootCause]` | 根因列表 |
| `corrective_actions` | `list[str]` | 纠正措施 |
| `similar_cases` | `list[SimilarCase]` | 相似案例 |

### `AlertRecord(BaseModel)`

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `int` | 告警 ID |
| `device_id` | `int` | 设备 ID |
| `defect_rate` | `float` | 缺陷率 |
| `threshold` | `float` | 阈值 |
| `status` | `str` | 状态 |
| `datapoint_code` | `str \| None` | 采集点编码 |
| `alert_time` | `str` | 告警时间 |

### `AlertsPageResponse(BaseModel)`

| 字段 | 类型 | 说明 |
|------|------|------|
| `records` | `list[AlertRecord]` | 告警记录 |
| `total` | `int` | 总数 |
| `page` | `int` | 当前页 |
| `size` | `int` | 每页条数 |
