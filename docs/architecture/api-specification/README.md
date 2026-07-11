# SMT Agent Platform API规范文档

**版本**: v1.1 | **日期**: 2026-07-11 | **状态**: Phase 3-4

---

## 文档索引

| 文件 | 章节 | 内容 |
|------|------|------|
| [01-overview.md](./01-overview.md) | 一 | 文档概述、分层架构 |
| [02-service-endpoints.md](./02-service-endpoints.md) | 二 | 服务端点清单、模块Agent文档 |
| [03-gateway-api.md](./03-gateway-api.md) | 三 | Java Gateway API（路由规则、JWT鉴权） |
| [04-device-service-api.md](./04-device-service-api.md) | 四 | Java Device Service API（设备CRUD、认证） |
| [05-scheduler-agent-api.md](./05-scheduler-agent-api.md) | 五 | Python Scheduler Agent API（订单管理、排产建议） |
| [06-maintenance-agent-api.md](./06-maintenance-agent-api.md) | 六 | Python Maintenance Agent API（健康诊断、故障诊断） |
| [07-quality-agent-api.md](./07-quality-agent-api.md) | 七 | Python Quality Agent API（质量告警、根因分析） |
| [08-knowledge-agent-api.md](./08-knowledge-agent-api.md) | 八 | Python Knowledge Agent API（知识问答、文档管理） |
| [09-orchestrator-agent-api.md](./09-orchestrator-agent-api.md) | 九 | Python Orchestrator Agent API（多Agent编排） |
| [10-execution-agent-api.md](./10-execution-agent-api.md) | 十 | Python Execution Agent API（指令管理） |
| [11-llm-service-api.md](./11-llm-service-api.md) | 十一 | 大模型服务 API（LLM 调用） |
| [12-middleware-api.md](./12-middleware-api.md) | 十二 | 中间件服务接口（PostgreSQL/Redis/InfluxDB/Milvus） |
| [13-call-chain-examples.md](./13-call-chain-examples.md) | 十三 | API调用链路示例 |
| [14-development-status.md](./14-development-status.md) | 十四 | 开发状态与已知问题 |
| [15-appendix.md](./15-appendix.md) | 十五 | 附录（测试脚本、重启命令） |
