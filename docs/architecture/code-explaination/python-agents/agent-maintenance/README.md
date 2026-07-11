# agent-maintenance 设备运维 Agent

> 设备预测性维护与故障诊断 Agent，提供健康评估、故障诊断（RAG+LLM）、预测性维护和案例管理。

**模块路径**: `python-agents/agent-maintenance/`
**端口**: 8002
**路径前缀**: `/v1/maintenance/`

## 职责

- 设备健康评估（基于 device-service 健康评分）
- 故障诊断（相似案例检索 + LLM 分析）
- 预测性维护（滑动均值 + 线性外推）
- 故障案例录入（Milvus 向量化存储）

## 模块结构

```
agent-maintenance/
├── main.py        ← FastAPI 入口 + 路由
├── diagnose.py    ← 故障诊断模块
├── predict.py     ← 预测性维护模块
└── models.py      ← Pydantic 模型
```

## 快速导航

| 模块 | 文档 | 说明 |
|------|------|------|
| main | [main](main.md) | FastAPI 路由与异常处理 |
| diagnose | [diagnose](diagnose.md) | 故障诊断核心逻辑 |
| predict | [predict](predict.md) | 预测性维护算法 |
| models | [models](models.md) | 请求/响应模型 |
