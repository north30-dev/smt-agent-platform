# Scripts 使用说明

本目录集中存放 SMT Agent Platform 的所有运维脚本。所有脚本均需在**项目根目录**下执行。

## 脚本清单

| 脚本 | 用途 | 执行命令 |
|------|------|---------|
| [config.sh](file:///home/north30/projects/Personal/smt-agent-platform/scripts/config.sh) | **共享配置**（端口/地址单一来源） | 被 source，不单独执行 |
| [build_all.sh](file:///home/north30/projects/Personal/smt-agent-platform/scripts/build_all.sh) | 全量构建（Java + Python） | `bash scripts/build_all.sh` |
| [start_all.sh](file:///home/north30/projects/Personal/smt-agent-platform/scripts/start_all.sh) | 从零冷启动所有服务（含 DB/Milvus 初始化） | `bash scripts/start_all.sh` |
| [dev_restart.sh](file:///home/north30/projects/Personal/smt-agent-platform/scripts/dev_restart.sh) | 重启已运行的开发服务（不初始化 DB） | `bash scripts/dev_restart.sh` |
| [stop_all.sh](file:///home/north30/projects/Personal/smt-agent-platform/scripts/stop_all.sh) | 停止所有服务（需确认 [Y/N]） | `bash scripts/stop_all.sh` |
| [init_db.sh](file:///home/north30/projects/Personal/smt-agent-platform/scripts/init_db.sh) | 手动初始化 PostgreSQL | `bash scripts/init_db.sh` |
| [api_integration_test.sh](file:///home/north30/projects/Personal/smt-agent-platform/scripts/api_integration_test.sh) | API 集成测试（12 项） | `bash scripts/api_integration_test.sh` |

---

## 详细说明

### 0. config.sh — 共享配置（端口/地址单一来源）

**用途**：集中管理所有脚本的端口、地址、API Key 配置。其他脚本通过 `source config.sh` 加载，避免硬编码。

**不单独执行**，由其他脚本自动 source。

**支持的配置项**（均可通过环境变量覆盖）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HOST` | `localhost` | 健康检查/测试请求的访问地址 |
| `BIND_HOST` | `0.0.0.0` | 服务实际绑定监听的地址 |
| `PG_PORT` | `5432` | PostgreSQL |
| `REDIS_PORT` | `6379` | Redis |
| `MQTT_PORT` | `1883` | Mosquitto |
| `INFLUX_PORT` | `8086` | InfluxDB |
| `MILVUS_PORT` | `19530` | Milvus |
| `JAVA_PORT` | `8081` | smt-device-service |
| `GATEWAY_PORT` | `8080` | smt-gateway |
| `SCHEDULER_PORT` | `8001` | agent-scheduler |
| `MAINTENANCE_PORT` | `8002` | agent-maintenance |
| `QUALITY_PORT` | `8003` | agent-quality |
| `KNOWLEDGE_PORT` | `8004` | agent-knowledge |
| `ORCHESTRATOR_PORT` | `8005` | agent-orchestrator |
| `LM_STUDIO_HOST` | `192.168.116.1` | LM Studio 主机（WSL 宿主机） |
| `LM_STUDIO_PORT` | `1234` | LM Studio 端口 |
| `LM_STUDIO_API_KEY` | `sk-lm-...` | LM Studio API Key |

**覆盖示例**：

```bash
# 临时改 Java 端口为 9090
SMT_JAVA_PORT=9090 bash scripts/start_all.sh

# 改 LM Studio 地址
LM_STUDIO_HOST=10.0.0.1 bash scripts/api_integration_test.sh

# 永久修改：直接编辑 config.sh
```

**预构造 URL**：config.sh 还提供 `JAVA_BASE`、`SCHEDULER_BASE` 等 `*_BASE` 变量（如 `JAVA_BASE=http://localhost:8081`），避免脚本里反复拼接字符串。

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

**输出示例**：

```
========== [1/3] 编译 C++ 原生层 ==========
[SKIP] cpp-native 暂未实现，跳过 C++ 构建
========== [2/3] 编译 Java 后端 ==========
[INFO] BUILD SUCCESS
========== [3/3] 编译 Python 智能体 ==========
Resolved X packages in Yms
========== 全量构建完成 ==========
```

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
| 中间件启动 | ✓ 按需启动（跳过 Kafka） | ✓ down + up |
| 等待中间件就绪 | ✓ TCP 端口探测 | ✗ 立即启动应用 |
| 数据库初始化 | ✓ 调用 init_db.sh | ✗ |
| Milvus 初始化 | ✓ init_collections | ✗ |
| 应用服务健康检查 | ✓ HTTP 探测 | ✗ |
| 失败即停止 | ✓ `set -euo pipefail` | ✗ |

**执行步骤**：

1. **前置依赖检查** — 检查 docker、mvn、uv、curl 是否安装，Docker daemon 是否运行
2. **启动中间件** — `docker compose up -d`（跳过 Kafka/Zookeeper 避免镜像 429）
3. **等待中间件就绪** — TCP 端口探测：PostgreSQL (5432)、Redis (6379)、Mosquitto (1883)、InfluxDB (8086)、Milvus (19530)
4. **初始化数据库** — 调用 `init_db.sh` 创建 Phase 3 表 + 插入测试设备
5. **初始化 Milvus** — 调用 `vector_store.init_collections(1024)` 创建 3 个 collection
6. **启动 Java 后端** — `mvn -pl smt-device-service spring-boot:run`（后台），等待 `/actuator/health` 返回 `UP`
7. **启动 Python 智能体** — 5 个 Agent（8001-8005）后台启动
8. **等待 Python Agent 就绪** — 逐个检查 `/healthz` 返回 `healthy`

**前置条件**：
- 已执行 `bash scripts/build_all.sh`（确保 Java 可编译、Python 依赖已装）
- Docker daemon 已运行
- 网络可访问 Maven Central 和 PyPI

**输出示例**：

```
[INFO]  检查前置依赖检查通过 ✓
[INFO]  启动中间件（跳过 Kafka/Zookeeper 以避免 429）...
[INFO]  等待中间件就绪...
[INFO]  PostgreSQL (端口 5432) 已就绪（3s）
[INFO]  Redis (端口 6379) 已就绪（1s）
[INFO]  Milvus (端口 19530) 已就绪（10s）
[INFO]  初始化数据库（Schema + 测试设备）...
[INFO]  初始化 Milvus Collections...
[INFO]  启动 Java 后端...
[INFO]  等待 smt-device-service 就绪...
[INFO]  smt-device-service 健康检查通过（15s）
[INFO]  启动 Python 智能体...
[INFO]  等待 Python 智能体就绪...
[INFO]  agent-8001 健康检查通过（3s）
==========================================
  冷启动完成 ✓
==========================================
```

---

### 3. stop_all.sh — 停止所有服务

**用途**：停止所有 Python Agent、Java 后端、中间件 Docker 容器。执行前需用户输入 `Y` 确认。

**执行命令**：

```bash
bash scripts/stop_all.sh
```

**执行步骤**：

1. **用户确认** — 列出即将停止的服务清单，等待 `[Y/N]` 输入。输入非 `Y/y/yes` 则取消
2. **停止 Python 智能体** — 5 个 Agent（双策略：PID 文件 + `pkill uvicorn` 兜底）
3. **停止 Java 后端** — 2 个模块（双策略：PID 文件 + `pkill spring-boot:run` 兜底）
4. **停止中间件容器** — `docker compose down`（兼容 v1/v2，失败则按容器名逐个停止）

**双策略停止机制**：

- **策略 1（PID 文件）**：读取 `logs/*.pid`，发送 `SIGTERM`，1 秒后仍存活则 `SIGKILL`
- **策略 2（进程名兜底）**：`pkill -f "uvicorn agent-*.main:app"` / `pkill -f "spring-boot:run.*smt-*"`
- 即使 PID 文件丢失或被手动清理，仍能正确停止服务

**安全设计**：
- ✓ 默认保留 Docker volumes（数据库数据不丢失）
- ✓ 明确提示"彻底清除数据需手动执行 `docker compose down -v`"
- ✓ Docker daemon 未运行时优雅跳过容器停止

**输出示例**：

```
==========================================
  即将停止以下服务：
==========================================
  应用服务（按 PID 文件 + 端口双策略）：
    Java device-service  (端口 8081)
    ...
⚠️  此操作会中断所有正在运行的 SMT 服务

确认停止所有服务？[Y/N] y
[INFO]  [1/3] 停止 Python 智能体...
[INFO]    agent-knowledge 已停止 ✓
...
[INFO]  [2/3] 停止 Java 后端...
[INFO]    smt-device-service 已停止 ✓
...
[INFO]  [3/3] 停止中间件 Docker 容器...
[INFO]    docker compose down 完成 ✓
[INFO]  ==========================================
[INFO]    所有服务已停止 ✓
```

---

### 4. dev_restart.sh — 重启所有本地开发服务

**用途**：一键重启中间件（Docker）+ Java 后端 + Python Agent，全部后台运行。

**执行命令**：

```bash
bash scripts/dev_restart.sh
```

**执行步骤**：

1. **重启中间件** — `cd docker-compose && docker-compose down && docker-compose up -d`
2. **[SKIP] C++ 原生层** — 暂未实现
3. **Java 后端** — 启动 `smt-device-service` (8081) + `smt-gateway` (8080)
4. **Python 智能体** — 启动 5 个 Agent：knowledge (8004)、maintenance (8002)、scheduler (8001)、quality (8003)、orchestrator (8005)

**前置条件**：
- Docker 已启动
- 已执行过 `bash scripts/build_all.sh`（确保 Java 可编译、Python 依赖已装）
- PostgreSQL 数据卷已存在且已初始化（首次需运行 `bash scripts/init_db.sh`）

**日志位置**：所有服务日志输出到 `logs/` 目录，PID 文件存于 `logs/*.pid`

**停止服务**：

```bash
# 方式 1：按 PID 文件停止
for pid_file in logs/*.pid; do kill $(cat "$pid_file") 2>/dev/null; done

# 方式 2：按进程名停止
pkill -f "uvicorn agent-"
pkill -f "smt-device-service"

# 停止中间件
cd docker-compose && docker compose down
```

**已知限制**：
- Kafka/Zookeeper 可能因镜像源 429 未启动（Phase 3 不依赖 Kafka，可忽略）
- `docker-compose` 命令使用 v1 语法，新版 Docker 建议改为 `docker compose`（v2）

---

### 5. init_db.sh — 手动初始化 PostgreSQL

**用途**：在已有数据卷上手动执行 Schema 创建和测试设备数据插入。适用于 Docker init 脚本未自动执行的场景（数据卷已存在数据时不会触发 `docker-entrypoint-initdb.d`）。

**执行命令**：

```bash
bash scripts/init_db.sh
```

**执行步骤**：

1. **创建 Phase 3 表** — 执行 `python-agents/shared/db_schema.sql`（创建 `quality_alerts`、`production_orders`、`production_plans` 三张表）
2. **插入测试设备数据** — 执行 `docker-compose/init/02-seed-devices.sql`（插入 4 台 SMT 设备：DEV-001 ~ DEV-004）
3. **验证表与数据** — 查询 `device`、`production_orders`、`quality_alerts` 记录数

**前置条件**：
- PostgreSQL 容器 `smt-postgres` 已启动
- 数据库 `smt`、用户 `smt` 已存在（由 docker-compose 初始化）

**输出示例**：

```
==> 创建 Phase 3 表...
CREATE TABLE
==> 插入测试设备数据...
INSERT 0 4
==> 验证表与数据...
    table_name     | count
-------------------+-------
 device            |     4
 production_orders |     0
 quality_alerts    |     0
==> 数据库初始化完成
```

**注意**：此脚本仅创建 Phase 3 新增的三张表和测试设备。`device` 表本身由 Java 侧的 Flyway/MyBatis-Plus 管理，本脚本只插入数据。

---

### 6. api_integration_test.sh — API 集成测试

**用途**：对运行中的 SMT Agent Platform 执行 12 项 API 集成测试，覆盖全部 6 个应用服务。

**执行命令**：

```bash
bash scripts/api_integration_test.sh
```

**测试项**：

| # | 测试项 | 目标服务 | 匹配模式 | 说明 |
|---|--------|---------|---------|------|
| 1 | Java device-service 健康检查 | Java (8081) | `UP` | `/actuator/health` |
| 2 | Java 设备数据查询 | Java (8081) | `deviceCode` | `/api/device/list` — 空数据算通过（服务正常） |
| 3 | JWT 认证 | Java (8081) | `token` | `/api/auth/login` |
| 4 | LM Studio 认证 | LM Studio (1234) | `data` | `/v1/models` |
| 5 | Scheduler 订单查询 | Scheduler (8001) | `order_no` | `/v1/scheduler/orders` — 空数据算通过 |
| 6 | Scheduler 订单创建 | Scheduler (8001) | `order_id` | POST `/v1/scheduler/orders` |
| 7 | Maintenance 设备健康分析 | Maintenance (8002) | `health_score` | `/v1/maintenance/health/1` |
| 8 | Quality 告警查询 | Quality (8003) | `"id"` | `/v1/quality/alerts` — 空数据算通过 |
| 9 | Quality 根因分析 | Quality (8003) | `root_cause` | POST `/v1/quality/root_cause` |
| 10 | Knowledge API 文档 | Knowledge (8004) | `fastapi` | `/docs` Swagger UI |
| 11 | Orchestrator 健康检查 | Orchestrator (8005) | `healthy` | `/healthz` |
| 12 | 设备故障协同编排 | Orchestrator (8005) | `workflow_id` | POST `/v1/orchestrator/device_fault` |

**前置条件**：
- 全部 6 个应用服务已启动（Java 8081 + Python 8001-8005）
- 中间件已启动（PostgreSQL、Redis、Milvus、MQTT）
- LM Studio 已启动且可访问
- 数据库已初始化（`bash scripts/init_db.sh`）
- Milvus collections 已创建（见下方说明）

**Milvus 初始化**（首次运行测试 9 前需执行一次）：

```bash
cd python-agents
uv run python -c "from shared import vector_store; vector_store.init_collections(1024)"
```

**判定逻辑**：
- 测试 2/5/8：使用 `is_service_healthy` 函数区分"服务错误"和"数据为空"。服务正常但数据空 → `✅ 通过 + ⚠️ 警告`
- 其余测试：使用 `test_api` 函数，响应中包含匹配模式即算通过
- 通过率 ≥ 50% → `⚠️ 部分失败`；通过率 < 50% → `❌ 多数失败`

**输出示例**：

```
==========================================
  SMT Agent Platform API集成测试
==========================================
[1] Java device-service健康检查
✅ 测试通过
...
[12] 设备故障协同编排测试
✅ 编排链路启动成功
==========================================
  测试结果汇总
==========================================
总测试数: 12
通过数: 12
失败数: 0
通过率: 100.0%
==========================================
🎉 所有测试通过！系统运行正常
```

**测试后清理**：

```bash
# 清理测试创建的订单
docker exec smt-postgres psql -U smt -d smt -c \
  "DELETE FROM production_orders WHERE order_no LIKE 'TEST-%' OR order_no LIKE 'URGENT-FAULT-%';"

# 清理临时文件
rm -f /tmp/orchestrator_result.json
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

# 重置数据库
docker exec -i smt-postgres psql -U smt -d smt <<'SQL'
DELETE FROM device WHERE deleted=0;
ALTER SEQUENCE device_id_seq RESTART WITH 1;
DELETE FROM production_orders;
DELETE FROM quality_alerts;
DELETE FROM production_plans;
SQL

# 重新初始化
bash scripts/init_db.sh
```

---

## 注意事项

1. **执行目录**：所有脚本必须在**项目根目录** `smt-agent-platform/` 下执行（脚本内已用 `PROJECT_ROOT` 自动定位，但相对路径仍需从根目录调用）
2. **Docker Compose 版本**：`dev_restart.sh` 使用 `docker-compose`（v1），新版 Docker 建议改为 `docker compose`（v2）
3. **Kafka 429 问题**：`dev_restart.sh` 启动中间件时若 Kafka/Zookeeper 镜像拉取失败（429），Phase 3 功能不受影响，可忽略
4. **日志文件**：`dev_restart.sh` 会在 `logs/` 目录生成各服务的 `.log` 和 `.pid` 文件，可查看日志排查问题
5. **端口冲突**：启动前请确保 8081、8001-8005、5432、6379、1883、8086、19530、9000-9001 端口未被占用
