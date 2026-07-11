# agent-orchestrator LangGraph 多智能体编排

> 基于 LangGraph 的多智能体编排服务，串联 maintenance → quality → scheduler → execution → summary 五个节点。

**模块路径**: `python-agents/agent-orchestrator/`
**端口**: 8005
**路径前缀**: `/v1/orchestrator/`

## 职责

- 设备故障编排入口（串行调用四个子 Agent）
- 工作流状态持久化（PostgreSQL）
- 降级处理（子 Agent 不可用时标记 skipped）
- LLM 汇总生成

## 模块结构

```
agent-orchestrator/
├── main.py           ← FastAPI 入口 + 路由
├── graph.py          ← LangGraph 编译图
├── nodes.py          ← 节点实现
├── state.py          ← 状态定义
├── agent_clients.py  ← 子 Agent HTTP 客户端
└── models.py         ← Pydantic 模型
```

## 编排流程

```
START → maintenance → quality → scheduler → execution → summary → END
```

线性图保证每个节点都执行，不会因某节点失败而短路。
