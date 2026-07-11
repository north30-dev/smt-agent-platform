# SMT Agent Platform 代码说明索引

> 全模块代码说明文档索引，按架构层组织。

---

## 架构层概览

```
┌─────────────────────────────────────────────────┐
│                   交互层                          │
│              (frontend - 未开放)                  │
├─────────────────────────────────────────────────┤
│                  网关层                           │
│              smt-gateway (8080)                  │
├─────────────────────────────────────────────────┤
│                 智能体层                          │
│  agent-scheduler (8001)  agent-maintenance (8002)│
│  agent-quality (8003)    agent-knowledge (8004)  │
│  agent-orchestrator (8005)                       │
├─────────────────────────────────────────────────┤
│                 服务层                           │
│         smt-device-service (8081)               │
│              smt-common (共享)                   │
├─────────────────────────────────────────────────┤
│                 数据层                           │
│  PostgreSQL │ Redis │ InfluxDB │ Milvus │ Kafka  │
└─────────────────────────────────────────────────┘
```

---

## Java 后端

| 模块 | 端口 | 说明 | 文档 |
|------|------|------|------|
| [smt-common](java-backend/smt-common/README.md) | — | 公共基础（响应封装/异常/安全/配置） | 13 个类文档 |
| [smt-gateway](java-backend/smt-gateway/README.md) | 8080 | API 网关（路由/JWT/CORS） | 3 个类文档 |
| [smt-device-service](java-backend/smt-device-service/README.md) | 8081 | 设备管理（CRUD/采集/健康评分） | 21 个类文档 |

---

## Python 智能体

| 模块 | 端口 | 说明 | 文档 |
|------|------|------|------|
| [shared](python-agents/shared/README.md) | — | 公共模块（LLM/向量库/DB/Kafka） | 10 个模块文档 |
| [agent-knowledge](python-agents/agent-knowledge/README.md) | 8004 | 知识助手（RAG 问答） | 4 个模块文档 |
| [agent-maintenance](python-agents/agent-maintenance/README.md) | 8002 | 设备运维（诊断/预测） | 4 个模块文档 |
| [agent-quality](python-agents/agent-quality/README.md) | 8003 | 质量分析（监控/根因） | 5 个模块文档 |
| [agent-scheduler](python-agents/agent-scheduler/README.md) | 8001 | 调度智能体（排产/急单） | 5 个模块文档 |
| [agent-orchestrator](python-agents/agent-orchestrator/README.md) | 8005 | 多智能体编排（LangGraph） | 6 个模块文档 |

---

## 基础设施

| 模块 | 说明 | 文档 |
|------|------|------|
| [docker-compose](infrastructure/docker-compose.md) | 服务编排（9 个中间件） | 1 个文档 |
| [api-contracts](infrastructure/api-contracts.md) | OpenAPI 规范 | 1 个文档 |
| [scripts](infrastructure/scripts.md) | 自动化脚本 | 1 个文档 |

---

## 未开放模块（暂不文档化）

| 模块 | 阶段 | 说明 |
|------|------|------|
| cpp-native | Phase 5 | C++ 原生层（空骨架） |
| frontend | Phase 4 | React 前端（空骨架） |
| agent-execution | Phase 4 | 执行协同 Agent |
| smt-order-service | Phase 4+ | 订单服务（空骨架） |
| smt-quality-service | Phase 4+ | 质量服务（空骨架） |
| smt-notification-service | Phase 4+ | 通知服务（空骨架） |
