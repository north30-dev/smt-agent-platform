# SMT Python Agents

SMT 贴片产线智能运维平台的 Python 智能体层。Phase 2 交付两个 Agent：

| Agent | 目录 | 端口 | 职责 |
|---|---|---|---|
| 知识助手 Agent | `agent-knowledge/` | 8004 | 文档入库 + RAG 问答（SOP/手册/工艺文件检索） |
| 设备运维 Agent | `agent-maintenance/` | 8002 | 设备健康分析 + 故障诊断 + 预测性维护 v1 |

## 依赖关系

- **大模型**：通过 `shared/llm_client.py` 统一调用（通义/DeepSeek/OpenAI 兼容接口）
- **向量库**：Milvus（`shared/vector_store.py` 封装），collection：`smt_knowledge`（知识库）、`smt_fault_cases`（故障案例）
- **Java device-service**：`agent-maintenance` 通过 HTTP 调用 `http://localhost:8081/api/device/{id}` 与 `/api/device/{id}/data`
- **网关**：经 `smt-gateway` 路由，外部访问 `http://localhost:8080/api/agent/knowledge/**` 与 `/api/agent/maintenance/**`

## 环境变量

复制 `.env.example` 为 `.env` 并填入真实值：

```bash
cp python-agents/.env.example python-agents/.env
```

关键变量：

| 变量 | 说明 |
|---|---|
| `LLM_PROVIDER` | 大模型提供商（tongyi/deepseek/openai） |
| `LLM_API_KEY` | 大模型 API Key（禁止硬编码到源码） |
| `LLM_BASE_URL` | 大模型 API Base URL |
| `LLM_MODEL` | 对话模型名 |
| `LLM_EMBED_MODEL` | Embedding 模型名 |
| `MILVUS_HOST` / `MILVUS_PORT` | Milvus 地址（默认 localhost:19530） |
| `DEVICE_SERVICE_BASE_URL` | Java device-service 地址（默认 http://localhost:8081） |

## 安装与启动

### 1. 安装依赖

```bash
cd python-agents
uv sync
```

### 2. 启动中间件

```bash
cd docker-compose
docker-compose up -d    # 启动 Milvus + etcd + minio 等
```

### 3. 启动 Agent

```bash
# 知识助手 Agent（端口 8004）
uv run uvicorn agent-knowledge.main:app --port 8004 --reload

# 设备运维 Agent（端口 8002）
uv run uvicorn agent-maintenance.main:app --port 8002 --reload
```

### 4. 运行测试

```bash
uv run pytest                    # 全部测试
uv run pytest tests/test_llm_client.py  # 单文件测试
```

## 目录结构

```
python-agents/
├── pyproject.toml                  # uv 依赖配置（PEP 621）
├── .env.example                    # 环境变量模板
├── README.md                       # 本文件
├── shared/                         # 公共模块
│   ├── llm_client.py               # 统一大模型调用
│   ├── vector_store.py             # Milvus 向量检索封装
│   ├── config.py                   # 配置加载（pydantic-settings）
│   └── prompts/
│       └── system_prompt.yaml      # 角色提示词
├── agent-knowledge/                # 知识助手 Agent（端口 8004）
│   ├── main.py                     # FastAPI 应用
│   ├── document_loader.py          # 文档加载与切分
│   ├── rag_chain.py                # RAG 流程
│   └── models.py                   # Pydantic 模型
├── agent-maintenance/              # 设备运维 Agent（端口 8002）
│   ├── main.py                     # FastAPI 应用
│   ├── device_client.py            # 调用 Java device-service
│   ├── diagnose.py                 # 故障诊断
│   ├── predict.py                  # 预测性维护 v1
│   └── models.py                   # Pydantic 模型
└── tests/                          # 单元测试
```

## 代码规范（AGENTS.md §3.2）

- 包名/目录名用 `kebab-case`（`agent-knowledge`、`agent-maintenance`）
- Python 导入用下划线模块名（`from shared.llm_client import chat`）
- 强制使用 Pydantic 做请求/响应模型校验
- 大模型调用统一走 `shared/llm_client.py`，禁止在各 Agent 内直接 new client
- 4 空格缩进、LF 换行、文件末尾保留空行
