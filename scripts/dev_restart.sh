#!/usr/bin/env bash
# 一键重启所有本地开发服务（中间件 + 各语言服务）
# 用法: bash scripts/dev_restart.sh

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 日志与 PID 目录（Phase 2 起 Python Agents 后台进程使用）
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

echo "========== [1/4] 重启中间件 =========="
cd "$PROJECT_ROOT/docker-compose"
docker-compose down
docker-compose up -d
cd "$PROJECT_ROOT"

echo "========== [2/4] 重启 C++ 原生层 =========="
echo "[SKIP] cpp-native 暂未实现，跳过"

echo "========== [3/4] 重启 Java 后端 =========="
# 先停掉旧进程（如有 PID 文件则 kill），沿用 [4/4] Python Agent 段的 PID 管理模式
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
echo "启动 smt-device-service (8081)..."
mvn -pl smt-device-service spring-boot:run > "$LOG_DIR/smt-device-service.log" 2>&1 &
echo $! > "$LOG_DIR/smt-device-service.pid"

echo "启动 smt-gateway (8080)..."
mvn -pl smt-gateway spring-boot:run > "$LOG_DIR/smt-gateway.log" 2>&1 &
echo $! > "$LOG_DIR/smt-gateway.pid"
cd "$PROJECT_ROOT"

echo "========== [4/4] 重启 Python 智能体 =========="
# ===== 启动 Python Agents（Phase 2 + Phase 3）=====
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

echo "启动 agent-knowledge (8004)..."
cd "$PROJECT_ROOT/python-agents"
uv run uvicorn agent-knowledge.main:app --port 8004 --host 0.0.0.0 > "$LOG_DIR/agent-knowledge.log" 2>&1 &
echo $! > "$LOG_DIR/agent-knowledge.pid"

echo "启动 agent-maintenance (8002)..."
uv run uvicorn agent-maintenance.main:app --port 8002 --host 0.0.0.0 > "$LOG_DIR/agent-maintenance.log" 2>&1 &
echo $! > "$LOG_DIR/agent-maintenance.pid"

# ===== Phase 3 新增 Agent（8001 调度 / 8003 质量 / 8005 编排）=====
# orchestrator 依赖 maintenance/quality/scheduler，因此最后启动
echo "启动 agent-scheduler (8001)..."
uv run uvicorn agent-scheduler.main:app --port 8001 --host 0.0.0.0 > "$LOG_DIR/agent-scheduler.log" 2>&1 &
echo $! > "$LOG_DIR/agent-scheduler.pid"

echo "启动 agent-quality (8003)..."
uv run uvicorn agent-quality.main:app --port 8003 --host 0.0.0.0 > "$LOG_DIR/agent-quality.log" 2>&1 &
echo $! > "$LOG_DIR/agent-quality.pid"

echo "启动 agent-orchestrator (8005)..."
uv run uvicorn agent-orchestrator.main:app --port 8005 --host 0.0.0.0 > "$LOG_DIR/agent-orchestrator.log" 2>&1 &
echo $! > "$LOG_DIR/agent-orchestrator.pid"
cd "$PROJECT_ROOT"

echo "========== 本地服务重启完成 =========="
