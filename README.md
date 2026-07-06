# smt-agent-platform

> SMT 贴片产线智能运维与调度系统 —— 面向电子制造 SMT 生产线的工业智能体平台，通过多智能体协同（调度、运维、质量、知识、执行）实现"感知—决策—规划—执行"全链路运营闭环。

## 技术栈

| 层 | 技术 | 版本 |
|----|------|------|
| Java 后端 | Spring Boot / Spring Cloud Gateway + Maven 多模块 | Java 21 |
| Python 智能体 | LangChain + FastAPI + Poetry | Python 3.12 |
| C++ 原生层 | CMake + pybind11 + JNI（仅输出动态库） | C++17 |
| 前端 | React + TypeScript + Vite + Ant Design + ECharts | React 18 / Vite 5 |
| 中间件 | Kafka、Redis、PostgreSQL、InfluxDB、Milvus、MinIO、Mosquitto | docker-compose 编排 |

四层架构 = 交互层 / 智能体层 / 服务层 / 数据层，详见 [docs/DIR.md](docs/DIR.md)。

## 已交付模块概览

### Java 后端（3 个 Maven 模块）

| 模块 | 端口 | 职责 |
|------|------|------|
| smt-common | — | 公共工具（Result/BizException/JwtUtil/MyBatis-Plus 基类） |
| smt-gateway | 8080 | API 网关（路由转发 + JWT 鉴权），统一代理设备服务与 Agent 接口 |
| smt-device-service | 8081 | 设备台账 CRUD + OPC UA/MQTT 双通道数据采集 + 健康评分 + InfluxDB 时序双写 |

### Python 智能体（2 个 Agent，8 个 REST 接口）

| Agent | 端口 | 接口 |
|-------|------|------|
| agent-knowledge | 8004 | 文档上传、RAG 问答、文档列表、文档删除 |
| agent-maintenance | 8002 | 设备健康评估、故障诊断（RAG + LLM）、预测性维护、故障案例入库 |

### 网关路由

| 路径 | 目标服务 | 鉴权 |
|------|----------|------|
| `/api/device/**` | smt-device-service:8081 | 放行 |
| `/api/agent/knowledge/**` | agent-knowledge:8004 | JWT |
| `/api/agent/maintenance/**` | agent-maintenance:8002 | JWT |

### 中间件（9 个 Docker 服务）

| 服务 | 阶段 | 用途 |
|------|------|------|
| PostgreSQL 16 | Phase 1 | 业务主库 |
| Redis 7 | Phase 1 | 缓存 + 会话 |
| Zookeeper 3.9 + Kafka 3.7 | Phase 1 | 事件流 |
| Mosquitto 2.0 | Phase 1 | MQTT 边缘接入 |
| etcd 3.5 | Phase 2 | Milvus 元数据 |
| MinIO | Phase 2 | 对象存储 |
| Milvus 2.4 | Phase 2 | 向量检索（RAG） |
| InfluxDB 2.7 | Phase 2 | 时序数据双写 |

## 快速开始

所有命令均在项目根目录执行。完整说明见 [AGENTS.md](AGENTS.md) §二。

### 1. 中间件（开发环境）

```bash
cd docker-compose
cp .env.example .env   # 按需填入生产值，.env 已被 .gitignore 排除
docker-compose up -d
```

### 2. Java 后端

```bash
cd java-backend
mvn clean install -DskipTests              # 全量编译安装
mvn -pl smt-gateway spring-boot:run        # 启动网关（端口 8080）
mvn -pl smt-device-service spring-boot:run # 启动设备服务（端口 8081）
mvn test                                    # 全量测试
```

### 3. Python 智能体

```bash
cd python-agents
uv sync
uv run pytest                                                   # 全部测试
uv run uvicorn agent-knowledge.main:app --port 8004 --reload   # 知识助手
uv run uvicorn agent-maintenance.main:app --port 8002 --reload # 运维 Agent
```

### 4. 前端

```bash
cd frontend
npm install
npm run dev        # 开发模式（端口 5173，代理 /api → 8080）
npm run build      # 生产构建
```

### 一键脚本

```bash
bash scripts/build_all.sh       # Java → Python 全量构建
bash scripts/dev_restart.sh     # 重启所有本地服务
```

## 项目阶段进展

| 阶段 | 状态 | 说明 |
|------|------|------|
| Phase 1 | 已完成 | 设备接入 + 数据采集 + API 网关 + InfluxDB 时序双写 + 可观测性基线；8 项 P0 + P1 问题修复 |
| Phase 2 | 已完成 | 知识助手 Agent（RAG）+ 设备运维 Agent + Milvus 向量库 + JWT 鉴权 + P0 修复与全量重构 |
| Phase 3 | 待启动 | 质量分析 Agent + 调度 Agent（LangGraph 多智能体编排） |
| Phase 4 | 规划中 | 执行协同 Agent + 全流程闭环（Kafka 事件驱动） |
| Phase 5 | 规划中 | 系统集成测试 + 产线试点 |

**测试覆盖**：Java 52 个单元测试 + Python 26 个测试全部通过。

**Phase 1 交付**：smt-common / smt-gateway / smt-device-service 三模块 + OPC UA + MQTT 双通道采集 + Redis 缓存 + InfluxDB 时序双写 + 结构化日志。详见 [Phase 1 说明](docs/explaination/project-explanation-phase1.md)。

**Phase 2 交付**：agent-knowledge（4 接口）+ agent-maintenance（4 接口）+ shared 公共模块（llm_client / vector_store / observability）+ Milvus RAG 链路 + 网关路由与鉴权 + API 版本化（/v1 前缀）。详见 [Phase 2 说明](docs/explaination/project-explanation-phase2.md)。

**未启动**：C++ 原生层（Phase 5 规划）、前端页面（骨架已搭建，待实际开发）。

## 文档索引

- [AGENTS.md](AGENTS.md) —— AI Agent 行为规范、构建命令、代码风格、安全边界、Git 工作流、报告输出规范
- [docs/PRD.md](docs/PRD.md) —— 产品需求文档
- [docs/DIR.md](docs/DIR.md) —— 目录骨架与四层架构说明
- [docs/architecture/](docs/architecture/) —— 架构设计文档
- [docs/database/](docs/database/) —— 数据库初始化脚本
- [docs/explaination/](docs/explaination/) —— 阶段说明文档
- [docs/repaired-reports/](docs/repaired-reports/) —— 修复与审查报告

## Git 工作流

- 分支：`main`（生产）/ `develop`（集成）/ `feature/*` / `fix/*` / `refactor/*` / `docs/*`
- 提交信息：Conventional Commits（`<type>(<scope>): <subject>`），详见 [AGENTS.md](AGENTS.md) §五
- 报告类文档统一输出到 `.trae/reports/` 或 `docs/repaired-reports/`，不随业务代码自动提交

## 安全约定

- 凭据统一通过环境变量注入（`${ENV:default}`），模板见 [docker-compose/.env.example](docker-compose/.env.example)
- `.env`、`*.key`、`*.pem`、`credentials.*` 等敏感文件已被 `.gitignore` 排除，禁止提交
- 完整安全边界见 [AGENTS.md](AGENTS.md) §四
