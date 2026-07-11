# 服务端点清单

**版本**: v1.1 | **日期**: 2026-07-11 | **状态**: Phase 3-4

---

## 二、服务端点清单

### 2.1 应用层服务

| 服务名称 | 基础URL | 端口 | 开发状态 |
|---------|---------|------|---------|
| **Java Gateway** | `http://localhost:8080` | 8080 | Phase 1 ✅ |
| **Java Device Service** | `http://localhost:8081` | 8081 | Phase 1 ✅ |
| **Scheduler Agent** | `http://localhost:8001` | 8001 | Phase 3 ✅ |
| **Maintenance Agent** | `http://localhost:8002` | 8002 | Phase 2 ✅ |
| **Quality Agent** | `http://localhost:8003` | 8003 | Phase 3 ✅ |
| **Knowledge Agent** | `http://localhost:8004` | 8004 | Phase 2 ✅ |
| **Orchestrator Agent** | `http://localhost:8005` | 8005 | Phase 3 ✅ |
| **Execution Agent** | `http://localhost:8006` | 8006 | Phase 3 ✅ |

### 2.2 大模型服务

| 服务名称 | 基础URL | 端口 | 备注 |
|---------|---------|------|------|
| **LLM Service** | `http://your-llm-service-url/v1` | 由部署配置决定 | 大模型推理服务 |

### 2.3 中间件服务

| 服务名称 | 基础URL | 端口 | 用途 |
|---------|---------|------|------|
| **PostgreSQL** | `localhost:5432` | 5432 | 关系型数据库（smt库） |
| **Redis** | `localhost:6380` | 6380 | 缓存与会话存储 |
| **InfluxDB** | `http://localhost:8086` | 8086 | 时序数据存储 |
| **Milvus** | `localhost:19530` | 19530 | 向量检索引擎 |
| **MinIO Console** | `http://localhost:9001` | 9001 | 对象存储管理界面 |
| **Mosquitto MQTT** | `tcp://localhost:1883` | 1883 | MQTT Broker |

### 2.4 模块 Agent 文档

每个模块目录下的 `.agent/` 文件夹存放该模块的说明文档，供 Agent 在执行任务前了解模块情况、执行后记录变更。

**文档清单（共 18 个文件）**：

| 模块 | 文件1 | 文件2（特有） | 文件3 |
|------|-------|-------------|-------|
| api-contracts | MODULE_OVERVIEW.md | API_REGISTRY.md | CHANGELOG.md |
| cpp-native | MODULE_OVERVIEW.md | ALGORITHM_REGISTRY.md | CHANGELOG.md |
| docker-compose | MODULE_OVERVIEW.md | NETWORK_ENV.md | CHANGELOG.md |
| frontend | MODULE_OVERVIEW.md | PAGE_REGISTRY.md | CHANGELOG.md |
| java-backend | MODULE_OVERVIEW.md | DATABASE_SCHEMA.md | CHANGELOG.md |
| python-agents | MODULE_OVERVIEW.md | AGENT_REGISTRY.md | CHANGELOG.md |

**Agent 行为规则**：

- 执行任务前：必须阅读模块 `.agent/MODULE_OVERVIEW.md`
- 执行任务后：必须更新 `.agent/CHANGELOG.md`
- 详见 AGENTS.md §7「模块 Agent 文档规范」
