#!/usr/bin/env bash
# 一键重启所有本地开发服务（中间件 + 各语言服务）
# 适用场景：服务已运行过，仅重启（不停中间件、不初始化 DB）
# 全新环境冷启动请用：bash scripts/start_all.sh
# 用法: bash scripts/dev_restart.sh

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 端口与地址配置（统一从 config.sh 读取，改端口改 config.sh 即可）
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

echo "========== [1/4] 检查中间件 =========="
# dev_restart 不重启中间件，仅检查是否在运行
cd "$PROJECT_ROOT/docker-compose"
# 检查 PostgreSQL 端口作为中间件是否运行的标志
if ss -tln 2>/dev/null | grep -q ":$PG_PORT "; then
    echo "中间件已运行 ✓"
else
    echo "[WARN] 中间件未运行，启动中间件（跳过 Kafka/Zookeeper 以避免 429）..."
    docker compose up -d postgres redis mosquitto influxdb etcd minio milvus 2>&1 | tail -5
    echo "等待中间件就绪..."
    for i in $(seq 1 30); do
        if ss -tln 2>/dev/null | grep -q ":$PG_PORT "; then break; fi
        sleep 1
    done
fi
cd "$PROJECT_ROOT"

echo "========== [2/4] 重启 C++ 原生层 =========="
echo "[SKIP] cpp-native 暂未实现，跳过"

echo "========== [3/4] 重启 Java 后端 =========="
# 先停掉旧进程（如有 PID 文件则 kill）
for module in smt-device-service smt-gateway; do
    if [ -f "$LOG_DIR/${module}.pid" ]; then
        old_pid=$(cat "$LOG_DIR/${module}.pid")
        if kill -0 "$old_pid" 2>/dev/null; then
            echo "停止旧 ${module} 进程 (pid=$old_pid)..."
            kill "$old_pid" || true
            sleep 1
        fi
        rm -f "$LOG_DIR/${module}.pid"
    fi
done

cd "$PROJECT_ROOT/java-backend"
echo "启动 smt-device-service ($JAVA_PORT)..."
mvn -pl smt-device-service spring-boot:run > "$LOG_DIR/smt-device-service.log" 2>&1 &
echo $! > "$LOG_DIR/smt-device-service.pid"

echo "启动 smt-gateway ($GATEWAY_PORT)..."
mvn -pl smt-gateway spring-boot:run > "$LOG_DIR/smt-gateway.log" 2>&1 &
echo $! > "$LOG_DIR/smt-gateway.pid"
cd "$PROJECT_ROOT"

echo "========== [4/4] 重启 Python 智能体 =========="
# 先停掉旧进程（如有 PID 文件则 kill）
for agent in agent-knowledge agent-maintenance agent-quality agent-scheduler agent-orchestrator; do
    if [ -f "$LOG_DIR/${agent}.pid" ]; then
        old_pid=$(cat "$LOG_DIR/${agent}.pid")
        if kill -0 "$old_pid" 2>/dev/null; then
            echo "停止旧 ${agent} 进程 (pid=$old_pid)..."
            kill "$old_pid" || true
            sleep 1
        fi
        rm -f "$LOG_DIR/${agent}.pid"
    fi
done

cd "$PROJECT_ROOT/python-agents"
echo "启动 agent-knowledge ($KNOWLEDGE_PORT)..."
uv run uvicorn agent-knowledge.main:app --port "$KNOWLEDGE_PORT" --host "$BIND_HOST" > "$LOG_DIR/agent-knowledge.log" 2>&1 &
echo $! > "$LOG_DIR/agent-knowledge.pid"

echo "启动 agent-maintenance ($MAINTENANCE_PORT)..."
uv run uvicorn agent-maintenance.main:app --port "$MAINTENANCE_PORT" --host "$BIND_HOST" > "$LOG_DIR/agent-maintenance.log" 2>&1 &
echo $! > "$LOG_DIR/agent-maintenance.pid"

# orchestrator 依赖 maintenance/quality/scheduler，因此最后启动
echo "启动 agent-scheduler ($SCHEDULER_PORT)..."
uv run uvicorn agent-scheduler.main:app --port "$SCHEDULER_PORT" --host "$BIND_HOST" > "$LOG_DIR/agent-scheduler.log" 2>&1 &
echo $! > "$LOG_DIR/agent-scheduler.pid"

echo "启动 agent-quality ($QUALITY_PORT)..."
uv run uvicorn agent-quality.main:app --port "$QUALITY_PORT" --host "$BIND_HOST" > "$LOG_DIR/agent-quality.log" 2>&1 &
echo $! > "$LOG_DIR/agent-quality.pid"

echo "启动 agent-orchestrator ($ORCHESTRATOR_PORT)..."
uv run uvicorn agent-orchestrator.main:app --port "$ORCHESTRATOR_PORT" --host "$BIND_HOST" > "$LOG_DIR/agent-orchestrator.log" 2>&1 &
echo $! > "$LOG_DIR/agent-orchestrator.pid"
cd "$PROJECT_ROOT"

echo "========== 本地服务重启完成 =========="
