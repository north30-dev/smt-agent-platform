#!/usr/bin/env bash
# 从零启动所有服务（中间件 + 数据库初始化 + Milvus + 应用服务）
# 适用场景：所有服务均未启动时（冷启动）
# 用法: bash scripts/start_all.sh
#
# 与 dev_restart.sh 的区别：
# - dev_restart.sh 假设服务已运行过，仅做重启（不停中间件、不初始化 DB）
# - start_all.sh 假设服务全部未启动，做完整冷启动（含依赖检查、等待就绪、DB 初始化）

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

# 端口与地址配置（统一从 config.sh 读取，改端口改 config.sh 即可）
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# 等待服务就绪（TCP 端口探测）
# 用法: wait_for_port <端口> <超时秒> <服务名>
wait_for_port() {
    local port="$1"
    local timeout="$2"
    local name="$3"
    local elapsed=0
    while ! ss -tln 2>/dev/null | grep -q ":$port " ; do
        if [ "$elapsed" -ge "$timeout" ]; then
            error "$name (端口 $port) 在 ${timeout}s 内未就绪"
            return 1
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done
    info "$name (端口 $port) 已就绪（${elapsed}s）"
}

# 等待 HTTP 健康检查通过
# 用法: wait_for_health <URL> <超时秒> <服务名> [期望模式]
wait_for_health() {
    local url="$1"
    local timeout="$2"
    local name="$3"
    local pattern="${4:-healthy}"
    local elapsed=0
    while ! curl -s --max-time 3 "$url" 2>/dev/null | grep -q "$pattern"; do
        if [ "$elapsed" -ge "$timeout" ]; then
            error "$name 健康检查未通过（${timeout}s）"
            return 1
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    info "$name 健康检查通过（${elapsed}s）"
}

echo "=========================================="
echo "  SMT Agent Platform 冷启动"
echo "=========================================="

# ========== 0. 前置依赖检查 ==========
info "检查前置依赖..."

check_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        error "未找到命令: $1 — 请先安装"
        exit 1
    fi
}

check_cmd docker
check_cmd mvn
check_cmd uv
check_cmd curl

# 检查 Docker daemon 是否运行
if ! docker info >/dev/null 2>&1; then
    error "Docker daemon 未运行，请先启动 Docker"
    exit 1
fi

info "前置依赖检查通过 ✓"

# ========== 1. 启动中间件 ==========
info "启动中间件..."
cd "$PROJECT_ROOT/docker-compose"
docker compose up -d postgres redis mosquitto influxdb etcd minio milvus zookeeper kafka 2>&1 | tail -5
cd "$PROJECT_ROOT"

info "等待中间件就绪..."
wait_for_port "$DB_PORT"         30 "PostgreSQL"   || exit 1
wait_for_port "$REDIS_PORT"      15 "Redis"         || exit 1
wait_for_port "$MQTT_PORT"       15 "Mosquitto"     || exit 1
wait_for_port "$INFLUX_PORT"     15 "InfluxDB"      || exit 1
wait_for_port "$MILVUS_PORT"     30 "Milvus"        || exit 1
wait_for_port "$ZOOKEEPER_PORT"  15 "Zookeeper"     || exit 1
wait_for_port "$KAFKA_PORT"      30 "Kafka"         || exit 1

# ========== 2. 初始化数据库 ==========
info "初始化数据库（Schema + 测试设备）..."
if ! docker exec smt-postgres pg_isready -U smt -d smt >/dev/null 2>&1; then
    error "PostgreSQL 未就绪，无法初始化"
    exit 1
fi

bash "$PROJECT_ROOT/scripts/init_db.sh"

# ========== 3. 初始化 Milvus Collections ==========
info "初始化 Milvus Collections..."
cd "$PROJECT_ROOT/python-agents"
if uv run python -c "from shared import vector_store; vector_store.init_collections(768)" 2>&1 | grep -q "Traceback"; then
    error "Milvus collection 初始化失败"
    exit 1
fi
info "Milvus Collections 初始化完成 ✓"
cd "$PROJECT_ROOT"

# ========== 4. 启动 Java 后端 ==========
info "启动 Java 后端..."

# 停止旧进程（如有 PID 文件）
for module in smt-device-service smt-gateway; do
    if [ -f "$LOG_DIR/${module}.pid" ]; then
        old_pid=$(cat "$LOG_DIR/${module}.pid")
        if kill -0 "$old_pid" 2>/dev/null; then
            warn "停止旧 ${module} 进程 (pid=$old_pid)..."
            kill "$old_pid" || true
            sleep 1
        fi
        rm -f "$LOG_DIR/${module}.pid"
    fi
done

cd "$PROJECT_ROOT/java-backend"
info "启动 smt-device-service ($DEVICE_SERVICE_PORT)..."
mvn -pl smt-device-service spring-boot:run > "$LOG_DIR/smt-device-service.log" 2>&1 &
echo $! > "$LOG_DIR/smt-device-service.pid"
cd "$PROJECT_ROOT"

info "等待 smt-device-service 就绪..."
wait_for_health "http://$HOST:$DEVICE_SERVICE_PORT/actuator/health" 60 "smt-device-service" "UP" || exit 1

cd "$PROJECT_ROOT/java-backend"
info "启动 smt-gateway ($GATEWAY_PORT)..."
mvn -pl smt-gateway spring-boot:run > "$LOG_DIR/smt-gateway.log" 2>&1 &
echo $! > "$LOG_DIR/smt-gateway.pid"
cd "$PROJECT_ROOT"

info "等待 smt-gateway 就绪..."
wait_for_health "http://$HOST:$GATEWAY_PORT/actuator/health" 60 "smt-gateway" "UP" || exit 1

# ========== 5. 启动 Python 智能体 ==========
info "启动 Python 智能体..."

# 停止旧进程
for agent in agent-knowledge agent-maintenance agent-quality agent-scheduler agent-orchestrator agent-execution; do
    if [ -f "$LOG_DIR/${agent}.pid" ]; then
        old_pid=$(cat "$LOG_DIR/${agent}.pid")
        if kill -0 "$old_pid" 2>/dev/null; then
            warn "停止旧 ${agent} 进程 (pid=$old_pid)..."
            kill "$old_pid" || true
            sleep 1
        fi
        rm -f "$LOG_DIR/${agent}.pid"
    fi
done

cd "$PROJECT_ROOT/python-agents"

info "启动 agent-scheduler ($SCHEDULER_PORT)..."
uv run uvicorn agent-scheduler.main:app --port "$SCHEDULER_PORT" --host "$BIND_HOST" > "$LOG_DIR/agent-scheduler.log" 2>&1 &
echo $! > "$LOG_DIR/agent-scheduler.pid"

info "启动 agent-maintenance ($MAINTENANCE_PORT)..."
uv run uvicorn agent-maintenance.main:app --port "$MAINTENANCE_PORT" --host "$BIND_HOST" > "$LOG_DIR/agent-maintenance.log" 2>&1 &
echo $! > "$LOG_DIR/agent-maintenance.pid"

info "启动 agent-quality ($QUALITY_PORT)..."
uv run uvicorn agent-quality.main:app --port "$QUALITY_PORT" --host "$BIND_HOST" > "$LOG_DIR/agent-quality.log" 2>&1 &
echo $! > "$LOG_DIR/agent-quality.pid"

info "启动 agent-knowledge ($KNOWLEDGE_PORT)..."
uv run uvicorn agent-knowledge.main:app --port "$KNOWLEDGE_PORT" --host "$BIND_HOST" > "$LOG_DIR/agent-knowledge.log" 2>&1 &
echo $! > "$LOG_DIR/agent-knowledge.pid"

info "启动 agent-orchestrator ($ORCHESTRATOR_PORT)..."
uv run uvicorn agent-orchestrator.main:app --port "$ORCHESTRATOR_PORT" --host "$BIND_HOST" > "$LOG_DIR/agent-orchestrator.log" 2>&1 &
echo $! > "$LOG_DIR/agent-orchestrator.pid"

info "启动 agent-execution ($EXECUTION_PORT)..."
uv run uvicorn agent-execution.main:app --port "$EXECUTION_PORT" --host "$BIND_HOST" > "$LOG_DIR/agent-execution.log" 2>&1 &
echo $! > "$LOG_DIR/agent-execution.pid"

cd "$PROJECT_ROOT"

# ========== 6. 等待所有 Python Agent 就绪 ==========
info "等待 Python 智能体就绪..."
for port in "$SCHEDULER_PORT" "$MAINTENANCE_PORT" "$QUALITY_PORT" "$KNOWLEDGE_PORT" "$ORCHESTRATOR_PORT" "$EXECUTION_PORT"; do
    wait_for_health "http://$HOST:$port/healthz" 30 "agent-$port" "healthy" || exit 1
done

# ========== 完成 ==========
echo ""
echo "=========================================="
echo "  冷启动完成 ✓"
echo "=========================================="
echo "服务清单："
echo "  中间件："
echo "    PostgreSQL  : $HOST:$DB_PORT"
echo "    Redis        : $HOST:$REDIS_PORT"
echo "    Mosquitto    : $HOST:$MQTT_PORT"
echo "    InfluxDB     : $HOST:$INFLUX_PORT"
echo "    Milvus       : $HOST:$MILVUS_PORT"
echo "    Zookeeper    : $HOST:$ZOOKEEPER_PORT"
echo "    Kafka        : $HOST:$KAFKA_PORT"
echo "  应用服务："
echo "    device-service  : http://$HOST:$DEVICE_SERVICE_PORT"
echo "    gateway         : http://$HOST:$GATEWAY_PORT"
echo "    scheduler       : http://$HOST:$SCHEDULER_PORT"
echo "    maintenance     : http://$HOST:$MAINTENANCE_PORT"
echo "    quality         : http://$HOST:$QUALITY_PORT"
echo "    knowledge       : http://$HOST:$KNOWLEDGE_PORT"
echo "    orchestrator    : http://$HOST:$ORCHESTRATOR_PORT"
echo "    execution       : http://$HOST:$EXECUTION_PORT"
echo ""
echo "日志位置: $LOG_DIR/"
echo "=========================================="
