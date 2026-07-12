# Scripts 使用说明

本目录集中存放 SMT Agent Platform 的所有运维脚本。所有脚本均需在**项目根目录**下执行。

## 脚本清单

| 脚本 | 用途 | 执行命令 |
|------|------|---------|
| config.sh | **共享配置**（端口/地址单一来源） | 被 source，不单独执行 |
| build_all.sh | 全量构建（Java + Python） | `bash scripts/build_all.sh` |
| start_all.sh | 从零冷启动所有服务（含 DB/Milvus 初始化） | `bash scripts/start_all.sh` |
| dev_restart.sh | 重启已运行的开发服务（不初始化 DB） | `bash scripts/dev_restart.sh` |
| stop_all.sh | 停止所有服务（需确认 [Y/N]） | `bash scripts/stop_all.sh` |
| init_db.sh | 手动初始化/清理 PostgreSQL | `bash scripts/init_db.sh` |
| api_integration_test.sh | API 集成测试（24 项） | `bash scripts/api_integration_test.sh` |

---

## 详细说明

### 0. config.sh — 共享配置（端口/地址单一来源）

**用途**：集中管理所有脚本的端口、地址配置。其他脚本通过 `source config.sh` 加载，避免硬编码。

**不单独执行**，由其他脚本自动 source。

**支持的配置项**（均可通过环境变量覆盖）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HOST` | `localhost` | 健康检查/测试请求的访问地址 |
| `BIND_HOST` | `0.0.0.0` | 服务实际绑定监听的地址 |
| `DB_PORT` | `5432` | PostgreSQL |
| `REDIS_PORT` | `6379` | Redis |
| `MQTT_PORT` | `1883` | Mosquitto |
| `INFLUX_PORT` | `8086` | InfluxDB |
| `MILVUS_PORT` | `19530` | Milvus |
| `KAFKA_PORT` | `9092` | Kafka |
| `ZOOKEEPER_PORT` | `2181` | Zookeeper |
| `DEVICE_SERVICE_PORT` | `8081` | smt-device-service |
| `GATEWAY_PORT` | `8080` | smt-gateway |
| `SCHEDULER_PORT` | `8001` | agent-scheduler |
| `MAINTENANCE_PORT` | `8002` | agent-maintenance |
| `QUALITY_PORT` | `8003` | agent-quality |
| `KNOWLEDGE_PORT` | `8004` | agent-knowledge |
| `ORCHESTRATOR_PORT` | `8005` | agent-orchestrator |
| `EXECUTION_PORT` | `8006` | agent-execution |
| `LLM_BASE_URL` | — | 大模型服务地址（从 `python-agents/.env` 读取） |
| `LLM_API_KEY` | — | 大模型 API Key（从 `python-agents/.env` 读取） |

**预构造 URL**：config.sh 还提供 `*_BASE` 变量（如 `DEVICE_SERVICE_BASE=http://localhost:8081`），避免脚本里反复拼接字符串。

---

### 1. build_all.sh — 全量构建

**用途**：依次编译 Java 后端和安装 Python 依赖。C++ 原生层暂未实现，自动跳过。

**执行命令**：

```bash
bash scripts/build_all.sh
```

**执行步骤**：

1. **[SKIP] C++ 原生层** — `cpp-native` 暂未实现，跳过
2. **Java 后端** — `cd java-backend && mvn clean install -DskipTests`
3. **Python 智能体** — `cd python-agents && uv sync`

**前置条件**：

- 已安装 Maven、JDK 21、uv
- 网络可访问 Maven Central 和 PyPI

---

### 2. start_all.sh — 从零冷启动所有服务

**用途**：在所有服务均未启动时，执行完整的冷启动流程：依赖检查 → 启动中间件 → 等待就绪 → 初始化数据库 → 初始化 Milvus → 启动应用服务 → 健康检查。

**执行命令**：

```bash
bash scripts/start_all.sh
```

**与 `dev_restart.sh` 的区别**：

| 维度 | `start_all.sh` | `dev_restart.sh` |
|------|----------------|------------------|
| 适用场景 | 全新环境/服务全部未启动 | 服务已运行过，仅重启 |
| 前置依赖检查 | ✓ 检查 docker/mvn/uv/curl | ✗ |
| 中间件启动 | ✓ 按需启动（含 Kafka/Zookeeper） | 检查后按需启动 |
| 等待中间件就绪 | ✓ TCP 端口探测 | ✗ 立即启动应用 |
| 数据库初始化 | ✓ 调用 init_db.sh | ✗ |
| Milvus 初始化 | ✓ init_collections(768) | ✗ |
| 应用服务健康检查 | ✓ HTTP 探测 | ✗ |
| 失败即停止 | ✓ `set -euo pipefail` | ✗ |

**执行步骤**：

1. **前置依赖检查** — 检查 docker、mvn、uv、curl 是否安装，Docker daemon 是否运行
2. **启动中间件** — `docker compose up -d`（含 Kafka/Zookeeper）
3. **等待中间件就绪** — TCP 端口探测：PostgreSQL (5432)、Redis (6379)、Mosquitto (1883)、InfluxDB (8086)、Milvus (19530)、Zookeeper (2181)、Kafka (9092)
4. **初始化数据库** — 调用 `init_db.sh` 创建全量表 + 插入种子设备
5. **初始化 Milvus** — 调用 `vector_store.init_collections(768)` 创建 3 个 collection
6. **启动 Java 后端** — `smt-device-service` (8081) + `smt-gateway` (8080)，等待 `/actuator/health` 返回 `UP`
7. **启动 Python 智能体** — 6 个 Agent（8001-8006）后台启动
8. **等待 Python Agent 就绪** — 逐个检查 `/healthz` 返回 `healthy`

**前置条件**：

- 已执行 `bash scripts/build_all.sh`（确保 Java 可编译、Python 依赖已装）
- Docker daemon 已运行

---

### 3. stop_all.sh — 停止所有服务

**用途**：停止所有 Python Agent、Java 后端、中间件 Docker 容器。执行前需用户输入 `Y` 确认。

**执行命令**：

```bash
bash scripts/stop_all.sh
```

**执行步骤**：

1. **用户确认** — 列出即将停止的服务清单，等待 `[Y/N]` 输入。输入非 `Y/y/yes` 则取消
2. **停止 Python 智能体** — 6 个 Agent（双策略：PID 文件 + `pkill uvicorn` 兜底）
3. **停止 Java 后端** — 2 个模块 smt-device-service + smt-gateway（双策略：PID 文件 + `pkill spring-boot:run` 兜底）
4. **停止中间件容器** — `docker compose down`（兼容 v1/v2，失败则按容器名逐个停止）

**双策略停止机制**：

- **策略 1（PID 文件）**：读取 `logs/*.pid`，发送 `SIGTERM`，1 秒后仍存活则 `SIGKILL`
- **策略 2（进程名兜底）**：`pkill -f "uvicorn agent-*.main:app"` / `pkill -f "spring-boot:run.*smt-*"`
- 即使 PID 文件丢失或被手动清理，仍能正确停止服务

**安全设计**：

- ✓ 默认保留 Docker volumes（数据库数据不丢失）
- ✓ 明确提示"彻底清除数据需手动执行 `docker compose down -v`"
- ✓ Docker daemon 未运行时优雅跳过容器停止

---

### 4. dev_restart.sh — 重启所有本地开发服务

**用途**：一键重启中间件（按需）+ Java 后端 + Python Agent，全部后台运行。

**执行命令**：

```bash
bash scripts/dev_restart.sh
```

**执行步骤**：

1. **检查中间件** — 若 PostgreSQL 端口未监听，则 `docker compose up -d` 启动全部中间件（含 Kafka/Zookeeper）
2. **[SKIP] C++ 原生层** — 暂未实现
3. **Java 后端** — 启动 `smt-device-service` (8081) + `smt-gateway` (8080)
4. **Python 智能体** — 启动 6 个 Agent：scheduler (8001)、maintenance (8002)、quality (8003)、knowledge (8004)、orchestrator (8005)、execution (8006)

**前置条件**：

- Docker 已启动
- 已执行过 `bash scripts/build_all.sh`（确保 Java 可编译、Python 依赖已装）
- PostgreSQL 数据卷已存在且已初始化（首次需运行 `bash scripts/init_db.sh`）

**日志位置**：所有服务日志输出到 `logs/` 目录，PID 文件存于 `logs/*.pid`

---

### 5. init_db.sh — 手动初始化/清理 PostgreSQL

**用途**：在已有数据卷上手动执行 Schema 创建和种子数据插入。适用于 Docker init 脚本未自动执行的场景（数据卷已存在数据时不会触发 `docker-entrypoint-initdb.d`）。

**执行命令**：

```bash
bash scripts/init_db.sh          # 初始化 schema + 种子数据
bash scripts/init_db.sh --clean  # 清理测试数据 → 重建 schema → 重插种子数据
```

**执行步骤（默认模式）**：

1. **创建全量表结构** — 执行 `database/init/01-schema.sql`（11 张表 DDL + 索引）
2. **插入种子数据** — 执行 `database/init/02-seed-devices.sql`（插入 4 台 SMT 设备：DEV-001 \~ DEV-004）
3. **验证表与数据** — 查询 `device`、`production_orders`、`quality_alerts` 记录数

**执行步骤（`--clean` 模式）**：

1. **清理测试数据** — 执行 `database/cleanup.sql`（清空 10 张表的测试数据，保留 device 表种子数据）
2. **重建全量表结构** — 执行 `database/init/01-schema.sql`
3. **重插种子数据** — 执行 `database/init/02-seed-devices.sql`
4. **验证表与数据**

**前置条件**：

- PostgreSQL 容器 `smt-postgres` 已启动
- 数据库 `smt`、用户 `smt` 已存在（由 docker-compose 初始化）

**SQL 脚本目录**（`database/`）：

| 文件 | 用途 | 自动执行 |
|------|------|---------|
| `init/01-schema.sql` | 全量 DDL（11 张表） | ✅ docker-compose up 首次 |
| `init/02-seed-devices.sql` | 设备种子数据 | ✅ docker-compose up 首次 |
| `cleanup.sql` | 清理测试脏数据 | ❌ 仅手动 |
| `seeds/03-seed-datapoints.sql` | 设备采集点定义 | ❌ 仅手动 |
| `seeds/04-seed-quality-baseline.sql` | 质量基线参数（预留） | ❌ 仅手动 |
| `seeds/05-seed-knowledge.md` | 知识库样例文档 | ❌ 通过 API 上传 |

---

### 6. api_integration_test.sh — API 集成测试

**用途**：对运行中的 SMT Agent Platform 执行 24 项 API 集成测试，覆盖全部 7 个应用服务。

**执行命令**：

```bash
bash scripts/api_integration_test.sh
```

**测试项**：

| # | 测试项 | 目标服务 | 匹配模式 | 说明 |
|---|--------|---------|---------|------|
| 1 | Java device-service 健康检查 | Java (8081) | `UP` | `/actuator/health` |
| 2 | Java 设备数据查询 | Java (8081) | `deviceCode` | `/api/device/list` — 空数据算通过 |
| 3 | JWT 认证 | Java (8081) | `token` | `/api/auth/login` |
| 4 | LM Studio 认证 | LM Studio | `data` | `/v1/models` |
| 5 | Scheduler 订单查询 | Scheduler (8001) | `order_no` | `/v1/scheduler/orders` — 空数据算通过 |
| 6 | Scheduler 订单创建 | Scheduler (8001) | `order_id` | POST `/v1/scheduler/orders` |
| 7 | Maintenance 设备健康分析 | Maintenance (8002) | `health_score` | `/v1/maintenance/health/1` |
| 8 | Quality 告警查询 | Quality (8003) | `"id"` | `/v1/quality/alerts` — 空数据算通过 |
| 9 | Quality 根因分析 | Quality (8003) | `root_cause` | POST `/v1/quality/root_cause` |
| 10 | Knowledge API 文档 | Knowledge (8004) | `fastapi` | `/docs` Swagger UI |
| 11 | Orchestrator 健康检查 | Orchestrator (8005) | `healthy` | `/healthz` |
| 12 | 设备故障协同编排 | Orchestrator (8005) | `workflow_id` | POST `/v1/orchestrator/device_fault` |
| 13 | Execution 健康检查 | Execution (8006) | `healthy` | `/healthz` |
| 14 | Execution 创建指令-手动-自动执行(LOW) | Execution (8006) | `APPROVED` | POST `/v1/execution/instructions` |
| 15 | Execution 创建指令-需审批(CRITICAL) | Execution (8006) | `PENDING_APPROVAL` | POST `/v1/execution/instructions` |
| 16 | Execution 指令列表查询 | Execution (8006) | `total` | `/v1/execution/instructions` |
| 17 | Execution 查询单条指令 | Execution (8006) | `instruction_id` | `/v1/execution/instructions/{id}` |
| 18 | Execution 查询不存在指令(404) | Execution (8006) | HTTP 404 | `/v1/execution/instructions/nonexistent` |
| 19 | Execution 审批指令(approve) | Execution (8006) | `APPROVED` | POST `/v1/execution/instructions/{id}/approve` |
| 20 | Execution 更新指令进度(EXECUTING) | Execution (8006) | `EXECUTING` | POST `/v1/execution/instructions/{id}/progress` |
| 21 | Execution 创建异常记录 | Execution (8006) | `exception_id` | POST `/v1/execution/exceptions` |
| 22 | Execution 异常列表查询 | Execution (8006) | 健康响应 | `/v1/execution/exceptions` |
| 23 | Execution 验证异常(passed) | Execution (8006) | `CLOSED` | POST `/v1/execution/exceptions/{id}/verify` |
| 24 | Orchestrator 设备故障事件编排 | Orchestrator (8005) | `workflow_id` + `instructions` | POST `/v1/orchestrator/device_fault_event` |

**前置条件**：

- 全部 7 个应用服务已启动（Java 8081 + Python 8001-8006）
- 中间件已启动（PostgreSQL、Redis、Milvus、MQTT）
- LM Studio 已启动且可访问
- 数据库已初始化（`bash scripts/init_db.sh`）
- Milvus collections 已创建（见下方说明）

**Milvus 初始化**（首次运行测试 9 前需执行一次）：

```bash
cd python-agents
uv run python -c "from shared import vector_store; vector_store.init_collections(768)"
```

**判定逻辑**：

- 测试 2/5/8：使用 `is_service_healthy` 函数区分"服务错误"和"数据为空"。服务正常但数据空 → `✅ 通过 + ⚠️ 警告`
- 其余测试：使用 `test_api` 函数，响应中包含匹配模式即算通过
- 通过率 ≥ 50% → `⚠️ 部分失败`；通过率 < 50% → `❌ 多数失败`

**测试后清理**：

```bash
# 清理测试创建的订单
docker exec smt-postgres psql -U smt -d smt -c \
  "DELETE FROM production_orders WHERE order_no LIKE 'TEST-%' OR order_no LIKE 'URGENT-FAULT-%';"

# 或使用清理脚本
bash scripts/init_db.sh --clean

# 清理临时文件
rm -f /tmp/orchestrator_result.json /tmp/orchestrator_event_result.json /tmp/execution_404.json
```

---

## 典型使用场景

### 场景 1：全新环境首次部署

```bash
# 1. 全量构建
bash scripts/build_all.sh

# 2. 一键冷启动（中间件 + DB 初始化 + Milvus 初始化 + 应用服务 + 健康检查）
bash scripts/start_all.sh

# 3. 运行集成测试验证
bash scripts/api_integration_test.sh
```

### 场景 2：日常开发迭代（服务已运行）

```bash
# 修改代码后重启应用服务（不停中间件、不初始化 DB）
bash scripts/dev_restart.sh

# 运行测试验证
bash scripts/api_integration_test.sh
```

### 场景 3：仅数据库重置

```bash
# 停止应用服务
pkill -f "uvicorn agent-"
pkill -f "smt-device-service"

# 清理测试数据并重建
bash scripts/init_db.sh --clean
```

---

## 注意事项

1. **执行目录**：所有脚本必须在**项目根目录** `smt-agent-platform/` 下执行（脚本内已用 `PROJECT_ROOT` 自动定位，但相对路径仍需从根目录调用）
2. **Docker Compose 版本**：脚本统一使用 `docker compose`（v2），不再兼容 `docker-compose`（v1）
3. **日志文件**：`dev_restart.sh` 和 `start_all.sh` 会在 `logs/` 目录生成各服务的 `.log` 和 `.pid` 文件，可查看日志排查问题
4. **端口冲突**：启动前请确保 8080-8081、8001-8006、5432、6379、1883、8086、19530、9092、2181、9000-9001 端口未被占用
5. **agent-execution**：端口 8006，Phase 4 新增的执行闭环 Agent，负责指令管理、审批、异常处置
