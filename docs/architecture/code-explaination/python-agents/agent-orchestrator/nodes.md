# agent-orchestrator/nodes

> LangGraph 节点函数，每个节点接收 OrchestratorState 并返回 partial state dict。

**模块路径**: `agent-orchestrator/nodes.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-orchestrator/nodes.py`

---

## 顶层函数

### `async maintenance_node(state: OrchestratorState) -> dict`

> 运维诊断节点

**逻辑**: 调用 `agent_clients.call_maintenance` → 成功返回 `{diagnosis: result}` → 失败返回 `{diagnosis: None, errors: merged}`

---

### `async quality_node(state: OrchestratorState) -> dict`

> 质量分析节点

**逻辑**: 调用 `agent_clients.call_quality` → 成功返回 `{quality_assessment: result}` → 失败返回 `{quality_assessment: {"status": "skipped"}, errors: merged}`

---

### `async scheduler_node(state: OrchestratorState) -> dict`

> 调度节点

**逻辑**: 构建合成急单（`URGENT-FAULT-{device_id}-{timestamp}`） → 调用 `agent_clients.call_scheduler` → 失败返回 skipped

---

### `async execution_node(state: OrchestratorState) -> dict`

> 执行节点（尽力而为）

**逻辑**: 若 diagnosis 和 schedule_adjustment 均为空/skipped → 返回空 instructions → 否则调用 `agent_clients.call_execution`

---

### `async summary_node(state: OrchestratorState) -> dict`

> 汇总节点

**逻辑**: 构建汇总提示词 → 调用 `llm_client.chat` → 返回 ≤300 字中文摘要 → LLM 失败返回固定降级文本

---

### `_merge_errors(current: dict[str, str], key: str, message: str) -> dict[str, str]`

> 合并错误字典

**逻辑**: 复制当前 errors dict → 添加新 key → 返回合并后的 dict

---

### `_build_summary_prompt(state: OrchestratorState) -> str`

> 构建汇总提示词

**逻辑**: 包含 device_id、symptom（`<user_input>` 标签）、diagnosis、quality_assessment、schedule_adjustment、instructions、降级节点列表
