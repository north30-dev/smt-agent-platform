# shared 公共模块

> Python Agent 公共基础模块，提供配置管理、LLM 调用、向量存储、数据库连接、Kafka 客户端等跨 Agent 复用能力。

**模块路径**: `python-agents/shared/`

## 职责

- 统一配置管理（pydantic-settings）
- 大模型调用封装（OpenAI 兼容接口）
- Milvus 向量库封装
- PostgreSQL 连接池管理
- Kafka 事件总线客户端
- 设备服务 HTTP 客户端
- 可观测性（结构化日志 + 健康检查）

## 模块结构

```
shared/
├── __init__.py
├── config.py            ← 应用配置（pydantic-settings）
├── llm_client.py        ← LLM 统一调用
├── vector_store.py      ← Milvus 向量存储
├── db.py                ← PostgreSQL 连接池 + 工作流持久化
├── models.py            ← 共享 Pydantic 模型
├── kafka_client.py      ← Kafka 客户端
├── observability.py     ← 可观测性
├── device_client.py     ← 设备服务 HTTP 客户端
├── doc_meta_store.py    ← 文档元数据存储
├── text_utils.py        ← 文本工具
└── prompts/
    └── system_prompt.yaml  ← LLM 提示词模板
```

## 快速导航

| 模块 | 文档 | 说明 |
|------|------|------|
| config | [config](config.md) | 应用配置管理 |
| llm_client | [llm_client](llm_client.md) | 大模型调用 |
| vector_store | [vector_store](vector_store.md) | Milvus 向量存储 |
| db | [db](db.md) | 数据库连接池 |
| models | [models](models.md) | 共享模型 |
| kafka_client | [kafka_client](kafka_client.md) | Kafka 客户端 |
| observability | [observability](observability.md) | 可观测性 |
| device_client | [device_client](device_client.md) | 设备服务客户端 |
| doc_meta_store | [doc_meta_store](doc_meta_store.md) | 文档元数据 |
| text_utils | [text_utils](text_utils.md) | 文本工具 |
