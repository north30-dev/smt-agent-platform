# smt-agent-platform

> SMT 贴片产线智能运维与调度系统 —— 面向电子制造 SMT 生产线的工业智能体平台，通过多智能体协同（调度、运维、质量、知识、执行）实现"感知—决策—规划—执行"全链路运营闭环。

## 技术栈

| 层 | 技术 | 版本 |
|----|------|------|
| Java 后端 | Spring Boot / Spring Cloud + Maven 多模块 | Java 21 |
| Python 智能体 | LangChain / LangGraph + FastAPI + Poetry | Python 3.12 |
| C++ 原生层 | CMake + pybind11 + JNI（仅输出动态库） | C++17 |
| 前端 | React + TypeScript + Vite + Ant Design + ECharts | React 18 / Vite 5 |
| 中间件 | Kafka、Redis、PostgreSQL、InfluxDB、Milvus | docker-compose 编排 |

四层架构 = 交互层 / 智能体层 / 服务层 / 数据层，详见 [docs/DIR.md](docs/DIR.md)。

## 快速开始

所有命令均在项目根目录执行。完整说明见 [AGENTS.md](AGENTS.md) §二。

### 1. 中间件（开发环境）

```bash
cd docker-compose
cp .env.example .env   # 按需填入生产值，.env 已被 .gitignore 排除
docker-compose up -d
```

### 2. C++ 原生层（最先编译）

```bash
cd cpp-native
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
```

### 3. Java 后端

```bash
cd java-backend
mvn clean install -DskipTests              # 全量编译安装
mvn -pl smt-device-service spring-boot:run  # 单服务运行
mvn test                                    # 全量测试
```

### 4. Python 智能体

```bash
cd python-agents
poetry install
poetry run pytest
```

### 5. 前端

```bash
cd frontend
npm install
npm run dev        # 开发模式（端口 5173，代理 /api → 8080）
npm run build      # 生产构建
```

### 一键脚本

```bash
bash scripts/build_all.sh       # C++ → Java → Python 全量构建
bash scripts/dev_restart.sh     # 重启所有本地服务
```

## 项目阶段进展

| 阶段 | 状态 | 说明 |
|------|------|------|
| Phase 1 | 收尾中 | 设备接入 + 数据采集 + RBAC 骨架 + 可观测性基线；本轮完成 8 项 P0 问题修复 |
| Phase 2 | 待启动 | 知识助手 Agent（RAG）+ 设备运维 Agent |
| Phase 3 | 规划中 | 质量分析 Agent + 调度 Agent（LangGraph 多智能体编排） |
| Phase 4 | 规划中 | 执行协同 Agent + 全流程闭环（Kafka 事件驱动） |
| Phase 5 | 规划中 | 系统集成测试 + 产线试点 |

**Phase 1 收尾 P0 修复**：3 个 Blocker + RBAC 骨架 + 凭据环境变量化 + OPC UA 配置化 + 可观测性 + 日志 Profile，共 8 项已全部修复并通过编译 + 52 个单元测试验证。详见 [Phase 1 P0 修复报告](docs/repaired-reports/p0-fix-report-phase1.md)。

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
