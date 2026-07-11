# agent-orchestrator/graph

> LangGraph 编译图定义，线性编排五个节点。

**模块路径**: `agent-orchestrator/graph.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-orchestrator/graph.py`

---

## 模块级对象

| 名称 | 类型 | 说明 |
|------|------|------|
| `app_graph` | `CompiledStateGraph` | 编译后的 LangGraph 图（模块加载时创建） |

---

## 顶层函数

### `build_graph() -> CompiledStateGraph`

> 构建并编译 LangGraph 图

**签名**: `def build_graph() -> CompiledStateGraph`

**返回值**: `CompiledStateGraph` — 编译后的图

**逻辑**:
1. 创建 `StateGraph(OrchestratorState)`
2. 添加 5 个节点
3. 添加线性边：START → maintenance → quality → scheduler → execution → summary → END
4. 返回 `g.compile()`

---

## 图结构

| 节点名 | 函数 | 输入状态 | 输出状态键 |
|--------|------|---------|-----------|
| `maintenance` | `maintenance_node` | `OrchestratorState` | `diagnosis`, `errors` |
| `quality` | `quality_node` | `OrchestratorState` | `quality_assessment`, `errors` |
| `scheduler` | `scheduler_node` | `OrchestratorState` | `schedule_adjustment`, `errors` |
| `execution` | `execution_node` | `OrchestratorState` | `instructions`, `errors` |
| `summary` | `summary_node` | `OrchestratorState` | `summary` |

| 边 | 源 | 目标 |
|---|---|------|
| 1 | START | maintenance |
| 2 | maintenance | quality |
| 3 | quality | scheduler |
| 4 | scheduler | execution |
| 5 | execution | summary |
| 6 | summary | END |
