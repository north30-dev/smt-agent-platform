# SMT Python Agents

SMT 贴片产线智能运维平台的 Python 智能体层。

- **Phase 2** 交付两个 Agent：知识助手（agent-knowledge）与设备运维（agent-maintenance）。
- **Phase 3** 新增三个 Agent：质量分析（agent-quality）、调度（agent-scheduler）、LangGraph 多 Agent 编排（agent-orchestrator）。

五个 Agent 各自独立运行 FastAPI 服务，端口 8001~8005；orchestrator 通过 REST 编排其余 Agent，形成"感知—诊断—评估—调度—执行"闭环。

| Agent | 目录 | 端口 | 职责 |
|---|---|---|---|
| 调度 Agent | `agent-scheduler/` | 8001 | 订单录入、智能排产、急单响应 |
| 设备运维 Agent | `agent-maintenance/` | 8002 | 设备健康分析、故障诊断、预测性维护 |
| 质量分析 Agent | `agent-quality/` | 8003 | 不良实时监控、根因分析、质量告警 |
| 知识助手 Agent | `agent-knowledge/` | 8004 | 文档入库 + RAG 问答（SOP/手册/工艺文件检索） |
| 编排 Agent | `agent-orchestrator/` | 8005 | LangGraph 多 Agent 协同编排 |

## 依赖关系

- **大模型**：通过 `shared/llm_client.py` 统一调用（通义/DeepSeek/OpenAI 兼容接口）
- **向量库**：Milvus（`shared/vector_store.py` 封装），collection：`smt_knowledge`（知识库）、`smt_fault_cases`（故障案例）
- **Java device-service**：`agent-maintenance` 通过 HTTP 调用 `http://localhost:8081/api/device/{id}` 与 `/api/device/{id}/data`
- **网关**：经 `smt-gateway` 路由，外部访问 `http://localhost:8080/api/agent/{knowledge|maintenance|quality|scheduler|orchestrator}/**`
- **编排**：`agent-orchestrator` 基于 LangGraph，通过 HTTP 调用 maintenance / quality / scheduler 三个 Agent 的 REST 接口完成跨 Agent 闭环

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
| `SMT_AGENT_SCHEDULER_HOST` / `SMT_AGENT_SCHEDULER_PORT` | 调度 Agent 网关路由地址（默认 localhost:8001） |
| `SMT_AGENT_QUALITY_HOST` / `SMT_AGENT_QUALITY_PORT` | 质量分析 Agent 网关路由地址（默认 localhost:8003） |
| `SMT_AGENT_ORCHESTRATOR_HOST` / `SMT_AGENT_ORCHESTRATOR_PORT` | 编排 Agent 网关路由地址（默认 localhost:8005） |
| `AGENT_MAINTENANCE_BASE_URL` | orchestrator 调用 maintenance Agent 的基地址（默认 http://localhost:8002） |
| `AGENT_QUALITY_BASE_URL` | orchestrator 调用 quality Agent 的基地址（默认 http://localhost:8003） |
| `AGENT_SCHEDULER_BASE_URL` | orchestrator 调用 scheduler Agent 的基地址（默认 http://localhost:8001） |

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
# 调度 Agent（端口 8001）
uv run uvicorn agent-scheduler.main:app --port 8001 --reload

# 设备运维 Agent（端口 8002）
uv run uvicorn agent-maintenance.main:app --port 8002 --reload

# 质量分析 Agent（端口 8003）
uv run uvicorn agent-quality.main:app --port 8003 --reload

# 知识助手 Agent（端口 8004）
uv run uvicorn agent-knowledge.main:app --port 8004 --reload

# 编排 Agent（端口 8005，依赖上述四个 Agent，最后启动）
uv run uvicorn agent-orchestrator.main:app --port 8005 --reload
```

### 4. 运行测试

```bash
uv run pytest                    # 全部测试
uv run pytest tests/test_llm_client.py  # 单文件测试
```

## 多 Agent 编排

`agent-orchestrator` 基于 LangGraph 编排 maintenance / quality / scheduler 三个 Agent，通过 REST 接口串联，形成跨 Agent 闭环决策。orchestrator 自身只做"图编排 + 状态机推进 + 子 Agent 结果汇总"，不重复实现业务逻辑。

### 编排依赖

- orchestrator → maintenance：`AGENT_MAINTENANCE_BASE_URL`（设备故障诊断）
- orchestrator → quality：`AGENT_QUALITY_BASE_URL`（不良影响评估）
- orchestrator → scheduler：`AGENT_SCHEDULER_BASE_URL`（排产调整建议）

### 典型场景：设备故障闭环

```
设备故障触发
    │
    ▼
maintenance（诊断）──► 故障原因 + 受影响设备
    │
    ▼
quality（评估）──► 是否波及批次质量 + 不良品范围
    │
    ▼
scheduler（调整排产）──► 换线建议 / 急单重排 / 产能再分配
    │
    ▼
闭环：编排结果回写，等待执行层（Phase 4）下发工单
```

### 调用入口

通过网关或直接访问 orchestrator：

```
POST /api/agent/orchestrator/device_fault
Content-Type: application/json

{
  "device_id": 1,
  "symptom": "贴片头 Z 轴异响，定位精度下降"
}
```

orchestrator 收到请求后，按上图顺序依次调用三个子 Agent，最终返回汇总的编排结果（诊断结论 + 质量影响 + 排产调整建议）。

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
├── agent-scheduler/                # 调度 Agent（端口 8001）
│   ├── main.py                     # FastAPI 应用
│   ├── planning.py                 # 智能排产
│   ├── urgent.py                   # 急单响应
│   ├── tools/                      # 产能计算等专属工具
│   └── models.py                   # Pydantic 模型
├── agent-maintenance/              # 设备运维 Agent（端口 8002）
│   ├── main.py                     # FastAPI 应用
│   ├── device_client.py            # 调用 Java device-service
│   ├── diagnose.py                 # 故障诊断
│   ├── predict.py                  # 预测性维护 v1
│   └── models.py                   # Pydantic 模型
├── agent-quality/                  # 质量分析 Agent（端口 8003）
│   ├── main.py                     # FastAPI 应用
│   ├── monitor.py                  # 不良实时监控
│   ├── root_cause.py               # 根因分析
│   └── models.py                   # Pydantic 模型
├── agent-knowledge/                # 知识助手 Agent（端口 8004）
│   ├── main.py                     # FastAPI 应用
│   ├── document_loader.py          # 文档加载与切分
│   ├── rag_chain.py                # RAG 流程
│   └── models.py                   # Pydantic 模型
├── agent-orchestrator/             # 编排 Agent（端口 8005）
│   ├── main.py                     # FastAPI 应用（编排入口）
│   ├── graph.py                    # LangGraph 多 Agent 图定义
│   ├── nodes.py                    # 图节点函数（调用各子 Agent）
│   └── models.py                   # Pydantic 模型
└── tests/                          # 单元测试
```

## 代码规范（AGENTS.md §3.2）

- 包名/目录名用 `kebab-case`（`agent-knowledge`、`agent-maintenance`、`agent-quality`、`agent-scheduler`、`agent-orchestrator`）
- Python 导入用下划线模块名（`from shared.llm_client import chat`）
- 强制使用 Pydantic 做请求/响应模型校验
- 大模型调用统一走 `shared/llm_client.py`，禁止在各 Agent 内直接 new client
- 4 空格缩进、LF 换行、文件末尾保留空行
