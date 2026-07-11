# agent-orchestrator/state

> LangGraph 共享状态定义。

**模块路径**: `agent-orchestrator/state.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-orchestrator/state.py`

---

## 类

### `OrchestratorState(TypedDict)`

> 编排流程共享状态

**字段**:

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `device_id` | `int` | — | 设备 ID |
| `symptom` | `str` | — | 故障症状 |
| `diagnosis` | `dict \| None` | `None` | 运维诊断结果 |
| `quality_assessment` | `dict \| None` | `None` | 质量分析结果 |
| `schedule_adjustment` | `dict \| None` | `None` | 调度调整结果 |
| `instructions` | `list[dict]` | `[]` | 执行指令列表 |
| `summary` | `str \| None` | `None` | 汇总文本 |
| `errors` | `dict[str, str]` | `{}` | 错误记录（key=节点名, value=错误信息） |
