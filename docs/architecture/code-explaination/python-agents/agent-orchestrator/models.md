# agent-orchestrator/models

> 编排 Agent 的 Pydantic 请求/响应模型。

**模块路径**: `agent-orchestrator/models.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-orchestrator/models.py`

---

## 类

### `DeviceFaultRequest(BaseModel)`

| 字段 | 类型 | 校验 | 说明 |
|------|------|------|------|
| `device_id` | `int` | `ge=1` | 设备 ID |
| `symptom` | `str` | `min_length=1, max_length=2000` | 故障症状 |

### `DeviceFaultEventRequest(BaseModel)`

| 字段 | 类型 | 校验 | 说明 |
|------|------|------|------|
| `device_id` | `int` | `ge=1` | 设备 ID |
| `symptom` | `str` | `min_length=1, max_length=2000` | 故障症状 |
| `source` | `str` | — | 来源，默认 "kafka" |

### `WorkflowResponse(BaseModel)`

| 字段 | 类型 | 说明 |
|------|------|------|
| `workflow_id` | `str` | 工作流 ID |
| `status` | `str` | 状态（SUCCESS/PARTIAL/FAILED） |
| `diagnosis` | `dict \| None` | 运维诊断结果 |
| `quality_assessment` | `dict \| None` | 质量分析结果 |
| `schedule_adjustment` | `dict \| None` | 调度调整结果 |
| `instructions` | `list` | 执行指令列表 |
| `summary` | `str \| None` | 汇总文本 |
| `errors` | `dict[str, str]` | 错误记录 |
