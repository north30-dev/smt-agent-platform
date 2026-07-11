# agent-quality 质量分析 Agent

> 质量分析 Agent，提供 AOI 缺陷监控、五因素根因分析、案例管理和告警查询。

**模块路径**: `python-agents/agent-quality/`
**端口**: 8003
**路径前缀**: `/v1/quality/`

## 职责

- 实时缺陷监控（AOI 缺陷率阈值判定）
- 根因分析（人/机/料/法/环五因素 + LLM）
- 质量案例录入（Milvus 向量化存储）
- 告警记录持久化与查询

## 模块结构

```
agent-quality/
├── main.py         ← FastAPI 入口 + 路由
├── monitor.py      ← 实时缺陷监控
├── root_cause.py   ← 根因分析
├── alert_store.py  ← 告警存储
└── models.py       ← Pydantic 模型
```

## 快速导航

| 模块 | 文档 | 说明 |
|------|------|------|
| main | [main](main.md) | FastAPI 路由 |
| monitor | [monitor](monitor.md) | 缺陷监控 |
| root_cause | [root_cause](root_cause.md) | 根因分析 |
| alert_store | [alert_store](alert_store.md) | 告警存储 |
| models | [models](models.md) | 请求/响应模型 |
