# agent-scheduler 调度智能体

> 生产调度 Agent，提供订单管理、排产计划生成、急单插单响应。

**模块路径**: `python-agents/agent-scheduler/`
**端口**: 8001
**路径前缀**: `/v1/scheduler/`

## 职责

- 订单录入与查询
- 排产计划生成（优先级+交付日期+物料齐套+设备状态）
- 急单插单响应（影响分析+调整建议）

## 模块结构

```
agent-scheduler/
├── main.py         ← FastAPI 入口 + 路由
├── planner.py      ← 排产计划生成
├── urgent.py       ← 急单处理
├── order_store.py  ← 订单存储
└── models.py       ← Pydantic 模型
```
