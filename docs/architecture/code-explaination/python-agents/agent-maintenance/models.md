# agent-maintenance/models

> 设备运维 Agent 的 Pydantic 请求/响应模型。

**模块路径**: `agent-maintenance/models.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-maintenance/models.py`

---

## 类

### `DiagnoseRequest(BaseModel)`

| 字段 | 类型 | 校验 | 说明 |
|------|------|------|------|
| `device_id` | `int` | `ge=1` | 设备 ID |
| `symptom` | `str` | `min_length=1, max_length=1000` | 故障症状描述 |

### `SimilarCase(BaseModel)`

| 字段 | 类型 | 说明 |
|------|------|------|
| `case_id` | `str` | 案例 ID |
| `symptom` | `str` | 症状 |
| `root_cause` | `str` | 根因 |
| `solution` | `str` | 解决方案 |
| `score` | `float` | 相似度得分 |

### `DiagnoseResponse(BaseModel)`

| 字段 | 类型 | 说明 |
|------|------|------|
| `root_causes` | `list[str]` | 根因列表 |
| `repair_suggestions` | `list[str]` | 维修建议 |
| `similar_cases` | `list[SimilarCase]` | 相似案例 |

### `HealthResponse(BaseModel)`

| 字段 | 类型 | 说明 |
|------|------|------|
| `device_id` | `int` | 设备 ID |
| `health_score` | `int` | 健康评分 |
| `status` | `str` | 设备状态 |
| `risk_level` | `str` | 风险等级（LOW/MEDIUM/HIGH） |
| `analysis` | `str` | 分析说明 |

### `ThresholdAlert(BaseModel)`

| 字段 | 类型 | 说明 |
|------|------|------|
| `datapoint_code` | `str` | 采集点编码 |
| `current_value` | `float` | 当前值 |
| `threshold` | `float` | 阈值 |
| `severity` | `str` | 严重程度 |

### `ForecastItem(BaseModel)`

| 字段 | 类型 | 说明 |
|------|------|------|
| `datapoint_code` | `str` | 采集点编码 |
| `predicted_value` | `float` | 预测值 |
| `hours_to_threshold` | `float \| None` | 距阈值小时数 |

### `PredictResponse(BaseModel)`

| 字段 | 类型 | 说明 |
|------|------|------|
| `trend` | `str` | 整体趋势 |
| `threshold_alerts` | `list[ThresholdAlert]` | 阈值告警 |
| `forecast` | `ForecastItem \| None` | 趋势预测 |
| `recommendation` | `str` | 运维建议 |
| `data_sufficient` | `bool` | 数据是否充足 |

### `CaseCreateRequest(BaseModel)`

| 字段 | 类型 | 说明 |
|------|------|------|
| `device_type` | `str` | 设备类型 |
| `symptom` | `str` | 故障症状 |
| `root_cause` | `str` | 根因 |
| `solution` | `str` | 解决方案 |

### `CaseCreateResponse(BaseModel)`

| 字段 | 类型 | 说明 |
|------|------|------|
| `case_id` | `str` | 生成的案例 ID |
