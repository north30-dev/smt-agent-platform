# agent-knowledge 知识助手 Agent

> 基于 RAG 的知识问答助手，提供文档上传、向量化存储、语义检索和大模型对话能力。

**模块路径**: `python-agents/agent-knowledge/`
**端口**: 8004
**路径前缀**: `/v1/knowledge/`

## 职责

- 文档上传与切分（支持 .md/.txt/.pdf/.docx）
- 向量化存储（Milvus）
- RAG 问答（检索→重排→生成）
- 文档管理（列表/删除）

## 模块结构

```
agent-knowledge/
├── main.py              ← FastAPI 入口 + 路由
├── rag_chain.py         ← RAG 流程封装
├── document_loader.py   ← 文档加载与切分
└── models.py            ← Pydantic 模型
```

## 快速导航

| 模块 | 文档 | 说明 |
|------|------|------|
| main | [main](main.md) | FastAPI 路由与异常处理 |
| rag_chain | [rag_chain](rag_chain.md) | RAG 核心流程 |
| document_loader | [document_loader](document_loader.md) | 文档加载与切分 |
| models | [models](models.md) | 请求/响应模型 |
