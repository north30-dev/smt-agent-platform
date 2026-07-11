#!/usr/bin/env bash
# 停止所有本地服务（Python Agent + Java 后端 + 中间件 Docker 容器）
# 用法: bash scripts/stop_all.sh
# 端口与地址配置见 scripts/config.sh

set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

LOG_DIR="$PROJECT_ROOT/logs"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ========== 用户确认 ==========
echo -e "${CYAN}=========================================="
echo "  即将停止以下服务："
echo -e "==========================================${NC}"
echo "  应用服务（按 PID 文件 + 端口双策略）："
echo "    Java device-service   (端口 $DEVICE_SERVICE_PORT)"
echo "    Java smt-gateway      (端口 $GATEWAY_PORT)"
echo "    agent-scheduler       (端口 $SCHEDULER_PORT)"
echo "    agent-maintenance     (端口 $MAINTENANCE_PORT)"
echo "    agent-quality         (端口 $QUALITY_PORT)"
echo "    agent-knowledge       (端口 $KNOWLEDGE_PORT)"
echo "    agent-orchestrator    (端口 $ORCHESTRATOR_PORT)"
echo "    agent-execution       (端口 $EXECUTION_PORT)"
echo "  中间件 Docker 容器："
echo "    postgres / redis / mosquitto / influxdb"
echo "    milvus / etcd / minio / kafka / zookeeper"
echo ""
echo -e "${YELLOW}⚠️  此操作会中断所有正在运行的 SMT 服务${NC}"
echo ""

read -r -p "确认停止所有服务？[Y/N] " answer
case "$answer" in
    [yY]|[yY][eE][sS])
        info "开始停止服务..."
        ;;
    *)
        warn "已取消，未做任何改动"
        exit 0
        ;;
esac

# ========== 1. 停止 Python 智能体 ==========
info "[1/3] 停止 Python 智能体..."
for agent in agent-knowledge agent-maintenance agent-quality agent-scheduler agent-orchestrator agent-execution; do
    stopped=false
    # 策略 1：PID 文件
    if [ -f "$LOG_DIR/${agent}.pid" ]; then
        pid=$(cat "$LOG_DIR/${agent}.pid")
        if kill -0 "$pid" 2>/dev/null; then
            info "  停止 ${agent} (pid=$pid)..."
            kill "$pid" 2>/dev/null || true
            sleep 1
            # 若仍未退出，强杀
            if kill -0 "$pid" 2>/dev/null; then
                warn "  ${agent} 未响应 SIGTERM，发送 SIGKILL..."
                kill -9 "$pid" 2>/dev/null || true
            fi
            stopped=true
        fi
        rm -f "$LOG_DIR/${agent}.pid"
    fi
    # 策略 2：按 uvicorn 进程名兜底
    pkill -f "uvicorn ${agent}.main:app" 2>/dev/null && stopped=true
    [ "$stopped" = true ] && info "  ${agent} 已停止 ✓" || warn "  ${agent} 未在运行"
done

# ========== 2. 停止 Java 后端 ==========
info "[2/3] 停止 Java 后端..."
for module in smt-device-service smt-gateway; do
    stopped=false
    # 策略 1：PID 文件
    if [ -f "$LOG_DIR/${module}.pid" ]; then
        pid=$(cat "$LOG_DIR/${module}.pid")
        if kill -0 "$pid" 2>/dev/null; then
            info "  停止 ${module} (pid=$pid)..."
            kill "$pid" 2>/dev/null || true
            sleep 3
            if kill -0 "$pid" 2>/dev/null; then
                warn "  ${module} 未响应 SIGTERM，发送 SIGKILL..."
                kill -9 "$pid" 2>/dev/null || true
            fi
            stopped=true
        fi
        rm -f "$LOG_DIR/${module}.pid"
    fi
    # 策略 2：按 mvn/spring-boot 进程名兜底
    pkill -f "spring-boot:run.*${module}" 2>/dev/null && stopped=true
    [ "$stopped" = true ] && info "  ${module} 已停止 ✓" || warn "  ${module} 未在运行"
done

# ========== 3. 停止中间件 Docker 容器 ==========
info "[3/3] 停止中间件 Docker 容器..."
if ! command -v docker >/dev/null 2>&1; then
    error "未找到 docker 命令，跳过容器停止"
else
    if ! docker info >/dev/null 2>&1; then
        warn "Docker daemon 未运行，跳过容器停止"
    else
        cd "$PROJECT_ROOT/docker-compose"
        # 尝试用 compose 停止（兼容 v1/v2）
        if docker compose down >/dev/null 2>&1; then
            info "  docker compose down 完成 ✓"
        elif docker-compose down >/dev/null 2>&1; then
            info "  docker-compose down 完成 ✓"
        else
            warn "  compose down 失败，尝试按容器名停止..."
            for c in smt-postgres smt-redis smt-mosquitto smt-influxdb smt-milvus smt-etcd smt-minio smt-kafka smt-zookeeper; do
                docker stop "$c" >/dev/null 2>&1 && info "  ${c} 已停止 ✓"
                docker rm "$c" >/dev/null 2>&1
            done
        fi
        cd "$PROJECT_ROOT"
    fi
fi

# ========== 完成 ==========
echo ""
info "=========================================="
info "  所有服务已停止 ✓"
info "=========================================="
info "说明："
info "  - Docker volumes 已保留（数据库 schema 与数据未删除）"
info "  - 若需彻底清除数据，请手动执行："
info "      cd docker-compose && docker compose down -v"
info "  - 应用 PID 文件已清理（若有残留请检查 $LOG_DIR/）"
