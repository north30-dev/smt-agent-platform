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
echo "[TODO] 各微服务请通过 mvn -pl <module> spring-boot:run 单独启动"

echo "========== [4/4] 重启 Python 智能体 =========="
# ===== 启动 Python Agents（Phase 2）=====
# 先停掉旧进程（如有 PID 文件则 kill）
for agent in agent-knowledge agent-maintenance; do
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
poetry run uvicorn agent-knowledge.main:app --port 8004 --host 0.0.0.0 > "$LOG_DIR/agent-knowledge.log" 2>&1 &
echo $! > "$LOG_DIR/agent-knowledge.pid"

echo "启动 agent-maintenance (8002)..."
poetry run uvicorn agent-maintenance.main:app --port 8002 --host 0.0.0.0 > "$LOG_DIR/agent-maintenance.log" 2>&1 &
echo $! > "$LOG_DIR/agent-maintenance.pid"
cd "$PROJECT_ROOT"

echo "========== 本地服务重启完成 =========="
