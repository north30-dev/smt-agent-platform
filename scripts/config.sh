#!/usr/bin/env bash
# scripts/config.sh — 所有运维脚本共享的端口与地址配置
# 改端口改这里即可，所有脚本自动生效。
# 用法：在脚本顶部 source 此文件：source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

# set -x

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
    SMT_DB_HOST="localhost"
    SMT_REDIS_HOST="localhost"
    SMT_MILVUS_HOST="localhost"
    SMT_DEVICE_SERVICE_HOST="localhost"
    SMT_KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
    SMT_MQTT_BROKER="tcp://localhost:1883"
fi

# 访问地址（健康检查 / 测试请求 / 输出展示）
HOST="${SMT_HOST:-localhost}"

# 服务实际绑定监听的地址（容器化部署时可改为 0.0.0.0）
BIND_HOST="${SMT_BIND_HOST:-0.0.0.0}"

# 中间件端口
DB_PORT="${SMT_DB_PORT:-5432}"      # postgres
REDIS_PORT="${SMT_REDIS_PORT:-6379}"  # redis
MQTT_PORT="${SMT_MQTT_PORT:-1883}"  # mosquitto
INFLUX_PORT="${SMT_INFLUX_PORT:-8086}" # influxdb
MILVUS_PORT="${SMT_MILVUS_PORT:-19530}" # milvus
KAFKA_PORT="${SMT_KAFKA_PORT:-9092}"   # kafka
ZOOKEEPER_PORT="${SMT_ZOOKEEPER_PORT:-2181}" # zookeeper

# 应用服务端口
# 设备服务
DEVICE_SERVICE_HOST="${SMT_DEVICE_SERVICE_HOST:-localhost}"
DEVICE_SERVICE_PORT="${SMT_DEVICE_SERVICE_PORT:-8081}"  # smt-device-service
# 网关服务
GATEWAY_HOST="${SMT_GATEWAY_HOST:-localhost}"
GATEWAY_PORT="${SMT_GATEWAY_PORT:-8080}"        # smt-gateway
# 调度器服务
SCHEDULER_HOST="${AGENT_SCHEDULER_HOST:-localhost}"
SCHEDULER_PORT="${AGENT_SCHEDULER_PORT:-8001}"    # agent-scheduler
# 维护服务
MAINTENANCE_HOST="${AGENT_MAINTENANCE_HOST:-localhost}"
MAINTENANCE_PORT="${AGENT_MAINTENANCE_PORT:-8002}"  # agent-maintenance
# 质量服务
QUALITY_HOST="${AGENT_QUALITY_HOST:-localhost}"
QUALITY_PORT="${AGENT_QUALITY_PORT:-8003}"        # agent-quality
# 知识库服务
KNOWLEDGE_HOST="${AGENT_KNOWLEDGE_HOST:-localhost}"
KNOWLEDGE_PORT="${AGENT_KNOWLEDGE_PORT:-8004}"   # agent-knowledge
# estrator服务
ORCHESTRATOR_HOST="${AGENT_ORCHESTRATOR_HOST:-localhost}"
ORCHESTRATOR_PORT="${AGENT_ORCHESTRATOR_PORT:-8005}" # agent-orchestrator
# 执行服务
EXECUTION_HOST="${AGENT_EXECUTION_HOST:-localhost}"
EXECUTION_PORT="${AGENT_EXECUTION_PORT:-8006}"      # agent-execution

# 大模型服务 — 从 python-agents/.env 的 LLM_BASE_URL 读取
LLM_BASE_URL="${LLM_BASE_URL:-http://your-llm-base-url/v1}"
# SEC-4：从环境变量读取，禁止硬编码密钥；未设置时仅告警，不阻断脚本
LLM_API_KEY="${LLM_API_KEY:-}"
if [ -z "$LLM_API_KEY" ]; then
    echo "⚠️ LLM_API_KEY 未设置，LLM 功能不可用" >&2
fi

# 构造完整 URL（避免脚本里反复拼接）
DEVICE_SERVICE_BASE="http://$DEVICE_SERVICE_HOST:$DEVICE_SERVICE_PORT"
GATEWAY_BASE="http://$GATEWAY_HOST:$GATEWAY_PORT"
SCHEDULER_BASE="http://$SCHEDULER_HOST:$SCHEDULER_PORT"
MAINTENANCE_BASE="http://$MAINTENANCE_HOST:$MAINTENANCE_PORT"
QUALITY_BASE="http://$QUALITY_HOST:$QUALITY_PORT"
KNOWLEDGE_BASE="http://$KNOWLEDGE_HOST:$KNOWLEDGE_PORT"
ORCHESTRATOR_BASE="http://$ORCHESTRATOR_HOST:$ORCHESTRATOR_PORT"
EXECUTION_BASE="http://$EXECUTION_HOST:$EXECUTION_PORT"


# 数据库连接（从 docker-compose/.env 读取，带 fallback）
DB_NAME="${SMT_DB_NAME:-smt}"
DB_USER="${SMT_DB_USERNAME:-smt}"
# 注意：运维脚本从宿主机连 PG，用 localhost + 宿主机映射端口，不用容器内地址
PG_CONTAINER_NAME="${PG_CONTAINER_NAME:-smt-postgres}"

# 管理员凭据（用于 JWT 认证测试）
# 注意：SMT_ADMIN_PASSWORD 是 BCrypt 哈希（供 device-service 读取），不是明文密码。
# 测试脚本发送的明文密码用 SMT_ADMIN_PASSWORD_PLAIN，默认 dev-only-admin
ADMIN_USERNAME="${SMT_ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${SMT_ADMIN_PASSWORD_PLAIN:-dev-only-admin}"
