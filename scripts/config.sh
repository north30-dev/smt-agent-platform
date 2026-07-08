#!/usr/bin/env bash
# scripts/config.sh — 所有运维脚本共享的端口与地址配置
# 改端口改这里即可，所有脚本自动生效。
# 用法：在脚本顶部 source 此文件：source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

# 安全加载 .env 文件（不回显内容，仅导出为环境变量）
# 用法：load_env_file <绝对路径>
load_env_file() {
    local env_file="$1"
    if [ -f "$env_file" ]; then
        set -a
        # shellcheck disable=SC1090
        source "$env_file"
        set +a
    fi
}

# 加载项目 .env 文件（PROJECT_ROOT 由调用脚本设置）
# 注意：docker-compose/.env 中的 HOST 变量（如 SMT_DB_HOST=postgres）是容器内网络名，
# 运维脚本从宿主机连接服务，需要覆盖回 localhost。
if [ -n "${PROJECT_ROOT:-}" ]; then
    load_env_file "$PROJECT_ROOT/docker-compose/.env"
    load_env_file "$PROJECT_ROOT/python-agents/.env"
    # 覆盖容器内网络名 → 宿主机可访问的地址
    SMT_DB_HOST="${SMT_DB_HOST_LOCAL:-localhost}"
    SMT_REDIS_HOST="${SMT_REDIS_HOST_LOCAL:-localhost}"
    SMT_MILVUS_HOST="${SMT_MILVUS_HOST_LOCAL:-localhost}"
    SMT_DEVICE_SERVICE_HOST="${SMT_DEVICE_SERVICE_HOST_LOCAL:-localhost}"
    SMT_KAFKA_BOOTSTRAP_SERVERS="${SMT_KAFKA_BOOTSTRAP_SERVERS_LOCAL:-localhost:9092}"
    SMT_MQTT_BROKER="${SMT_MQTT_BROKER_LOCAL:-tcp://localhost:1883}"
fi

# 访问地址（健康检查 / 测试请求 / 输出展示）
HOST="${SMT_HOST:-localhost}"

# 服务实际绑定监听的地址（容器化部署时可改为 0.0.0.0）
BIND_HOST="${SMT_BIND_HOST:-0.0.0.0}"

# 中间件端口
PG_PORT="${SMT_PG_PORT:-5432}"
REDIS_PORT="${SMT_REDIS_PORT:-6379}"
MQTT_PORT="${SMT_MQTT_PORT:-1883}"
INFLUX_PORT="${SMT_INFLUX_PORT:-8086}"
MILVUS_PORT="${SMT_MILVUS_PORT:-19530}"
KAFKA_PORT="${SMT_KAFKA_PORT:-9092}"
ZOOKEEPER_PORT="${SMT_ZOOKEEPER_PORT:-2181}"

# 应用服务端口
JAVA_PORT="${SMT_JAVA_PORT:-8081}"               # smt-device-service
GATEWAY_PORT="${SMT_GATEWAY_PORT:-8080}"        # smt-gateway
SCHEDULER_PORT="${SMT_SCHEDULER_PORT:-8001}"    # agent-scheduler
MAINTENANCE_PORT="${SMT_MAINTENANCE_PORT:-8002}"  # agent-maintenance
QUALITY_PORT="${SMT_QUALITY_PORT:-8003}"        # agent-quality
KNOWLEDGE_PORT="${SMT_KNOWLEDGE_PORT:-8004}"   # agent-knowledge
ORCHESTRATOR_PORT="${SMT_ORCHESTRATOR_PORT:-8005}" # agent-orchestrator

# 大模型服务（LM Studio）— 默认指向 WSL 宿主机
LM_STUDIO_HOST="${LM_STUDIO_HOST:-192.168.116.1}"
LM_STUDIO_PORT="${LM_STUDIO_PORT:-1234}"
LM_STUDIO_API_KEY="${LM_STUDIO_API_KEY:-sk-lm-dbMlwJNn:IJyAOrh0mrvZ6eeJJ2OA}"

# 构造完整 URL（避免脚本里反复拼接）
JAVA_BASE="http://$HOST:$JAVA_PORT"
GATEWAY_BASE="http://$HOST:$GATEWAY_PORT"
SCHEDULER_BASE="http://$HOST:$SCHEDULER_PORT"
MAINTENANCE_BASE="http://$HOST:$MAINTENANCE_PORT"
QUALITY_BASE="http://$HOST:$QUALITY_PORT"
KNOWLEDGE_BASE="http://$HOST:$KNOWLEDGE_PORT"
ORCHESTRATOR_BASE="http://$HOST:$ORCHESTRATOR_PORT"
LM_STUDIO_BASE="http://$LM_STUDIO_HOST:$LM_STUDIO_PORT"

# 数据库连接（从 docker-compose/.env 读取，带 fallback）
DB_NAME="${SMT_DB_NAME:-smt}"
DB_USER="${SMT_DB_USERNAME:-smt}"
# 注意：运维脚本从宿主机连 PG，用 localhost + 宿主机映射端口，不用容器内地址
PG_CONTAINER_NAME="${PG_CONTAINER_NAME:-smt-postgres}"

# 管理员凭据（用于 JWT 认证测试，从 docker-compose/.env 读取）
ADMIN_USERNAME="${SMT_ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${SMT_ADMIN_PASSWORD:-dev-only-admin}"
