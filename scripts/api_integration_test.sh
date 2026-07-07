#!/bin/bash

# ========================================
# SMT Agent Platform API集成测试脚本
# 端口与地址配置见 scripts/config.sh
# ========================================

# 设置 PROJECT_ROOT 以便 config.sh 加载 .env
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 加载配置
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

echo "=========================================="
echo "  SMT Agent Platform API集成测试"
echo "=========================================="

# 测试计数器
TOTAL_TESTS=0
PASS_TESTS=0
FAIL_TESTS=0

# 检查服务响应是否健康（非错误响应）
# 用法：is_service_healthy "$response"
# 返回 0=健康，1=服务异常
is_service_healthy() {
    local response="$1"
    # 空响应 = 服务不可达
    if [ -z "$response" ]; then
        return 1
    fi
    # Python 错误响应含 "error" 字段
    if echo "$response" | grep -q '"error"'; then
        return 1
    fi
    # Java 错误响应 code 为 4xx/5xx
    if echo "$response" | grep -qE '"code":[45][0-9][0-9]'; then
        return 1
    fi
    return 0
}

# 测试函数
test_api() {
    local test_name="$1"
    local test_command="$2"
    local expected_pattern="$3"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo ""
    echo "[$TOTAL_TESTS] $test_name"

    if eval "$test_command" | grep -q "$expected_pattern"; then
        echo "✅ 测试通过"
        PASS_TESTS=$((PASS_TESTS + 1))
    else
        echo "❌ 测试失败"
        FAIL_TESTS=$((FAIL_TESTS + 1))
    fi
}

# 1. Java设备服务健康检查
test_api "Java device-service健康检查" \
    "curl -s $JAVA_BASE/actuator/health" \
    "UP"

# 2. Java设备数据查询
DEVICE_RESPONSE=$(curl -s "$JAVA_BASE/api/device/list?page=1&size=10" 2>/dev/null)
DEVICE_COUNT=$(echo "$DEVICE_RESPONSE" | grep -o "deviceCode" | wc -l)
TOTAL_TESTS=$((TOTAL_TESTS + 1))
echo ""
echo "[2] Java设备数据查询"
if is_service_healthy "$DEVICE_RESPONSE"; then
    echo "设备数量: $DEVICE_COUNT条"
    if [ "$DEVICE_COUNT" -gt 0 ]; then
        echo "✅ 测试通过"
    else
        echo "⚠️ 设备数据为空，服务正常"
    fi
    PASS_TESTS=$((PASS_TESTS + 1))
else
    echo "❌ 测试失败（服务异常）"
    echo "响应: $(echo "$DEVICE_RESPONSE" | head -c 200)"
    FAIL_TESTS=$((FAIL_TESTS + 1))
fi

# 3. JWT认证测试
TOTAL_TESTS=$((TOTAL_TESTS + 1))
echo ""
echo "[3] JWT认证"
JWT_RESPONSE=$(curl -s -X POST "$JAVA_BASE/api/auth/login" -H 'Content-Type: application/json' -d "{\"username\":\"$ADMIN_USERNAME\",\"password\":\"$ADMIN_PASSWORD\"}")
if echo "$JWT_RESPONSE" | grep -q "token"; then
    echo "✅ 测试通过"
    PASS_TESTS=$((PASS_TESTS + 1))
else
    echo "❌ 测试失败"
    echo "响应: $(echo "$JWT_RESPONSE" | head -c 200)"
    FAIL_TESTS=$((FAIL_TESTS + 1))
fi

# 4. LM Studio大模型服务
test_api "LM Studio认证" \
    "curl -s $LM_STUDIO_BASE/v1/models -H 'Authorization: Bearer $LM_STUDIO_API_KEY'" \
    "data"

# 5. Scheduler Agent订单查询
ORDER_RESPONSE=$(curl -s "$SCHEDULER_BASE/v1/scheduler/orders" 2>/dev/null)
ORDER_COUNT=$(echo "$ORDER_RESPONSE" | grep -o "order_no" | wc -l)
TOTAL_TESTS=$((TOTAL_TESTS + 1))
echo ""
echo "[5] Scheduler订单查询"
if is_service_healthy "$ORDER_RESPONSE"; then
    echo "订单数量: $ORDER_COUNT条"
    if [ "$ORDER_COUNT" -gt 0 ]; then
        echo "✅ 测试通过"
    else
        echo "⚠️ 订单数据为空，服务正常"
    fi
    PASS_TESTS=$((PASS_TESTS + 1))
else
    echo "❌ 测试失败（服务异常）"
    echo "响应: $(echo "$ORDER_RESPONSE" | head -c 200)"
    FAIL_TESTS=$((FAIL_TESTS + 1))
fi

# 6. Scheduler Agent订单创建
TOTAL_TESTS=$((TOTAL_TESTS + 1))
echo ""
echo "[6] Scheduler订单创建"
UNIQUE_ORDER_NO="TEST-API-$(date +%s)"
ORDER_CREATE_RESPONSE=$(curl -s -X POST "$SCHEDULER_BASE/v1/scheduler/orders" -H 'Content-Type: application/json' -d "{\"order_no\":\"$UNIQUE_ORDER_NO\",\"product_model\":\"主板\",\"quantity\":100,\"priority\":\"HIGH\",\"delivery_date\":\"2026-07-10\"}")
if echo "$ORDER_CREATE_RESPONSE" | grep -q "order_id"; then
    echo "✅ 测试通过"
    PASS_TESTS=$((PASS_TESTS + 1))
else
    echo "❌ 测试失败"
    echo "响应: $(echo "$ORDER_CREATE_RESPONSE" | head -c 200)"
    FAIL_TESTS=$((FAIL_TESTS + 1))
fi

# 7. Maintenance Agent健康分析
test_api "Maintenance设备健康分析" \
    "curl -s $MAINTENANCE_BASE/v1/maintenance/health/1" \
    "health_score"

# 8. Quality Agent告警查询
ALERT_RESPONSE=$(curl -s "$QUALITY_BASE/v1/quality/alerts" 2>/dev/null)
ALERT_COUNT=$(echo "$ALERT_RESPONSE" | grep -o "\"id\"" | wc -l)
TOTAL_TESTS=$((TOTAL_TESTS + 1))
echo ""
echo "[8] Quality告警查询"
if is_service_healthy "$ALERT_RESPONSE"; then
    echo "告警数量: $ALERT_COUNT条"
    if [ "$ALERT_COUNT" -gt 0 ]; then
        echo "✅ 测试通过"
    else
        echo "⚠️ 告警数据为空，服务正常"
    fi
    PASS_TESTS=$((PASS_TESTS + 1))
else
    echo "❌ 测试失败（服务异常）"
    echo "响应: $(echo "$ALERT_RESPONSE" | head -c 200)"
    FAIL_TESTS=$((FAIL_TESTS + 1))
fi

# 9. Quality Agent根因分析
test_api "Quality根因分析" \
    "curl -s -X POST $QUALITY_BASE/v1/quality/root_cause -H 'Content-Type: application/json' -d '{\"device_id\":1,\"defect_description\":\"AOI检测不良率超标\"}'" \
    "root_cause"

# 10. Knowledge Agent文档查询
test_api "Knowledge API文档" \
    "curl -s $KNOWLEDGE_BASE/docs" \
    "fastapi"

# 11. Orchestrator Agent健康检查
test_api "Orchestrator健康检查" \
    "curl -s $ORCHESTRATOR_BASE/healthz" \
    "healthy"

# 12. 完整编排链路测试
echo "[12] 设备故障协同编排测试"
curl -s -X POST "$ORCHESTRATOR_BASE/v1/orchestrator/device_fault" \
  -H 'Content-Type: application/json' \
  -d '{"device_id":1,"symptom":"温度异常，振动增大"}' > /tmp/orchestrator_result.json

if grep -q "workflow_id" /tmp/orchestrator_result.json; then
    echo "✅ 编排链路启动成功"
    cat /tmp/orchestrator_result.json
    PASS_TESTS=$((PASS_TESTS + 1))
else
    echo "❌ 编排链路启动失败"
    cat /tmp/orchestrator_result.json
    FAIL_TESTS=$((FAIL_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# ========================================
# 测试结果汇总
# ========================================

echo ""
echo "=========================================="
echo "  测试结果汇总"
echo "=========================================="
echo "总测试数: $TOTAL_TESTS"
echo "通过数: $PASS_TESTS"
echo "失败数: $FAIL_TESTS"
echo "通过率: $(awk "BEGIN {printf \"%.1f\", ($PASS_TESTS/$TOTAL_TESTS)*100}")%"
echo "=========================================="

if [ "$FAIL_TESTS" -eq 0 ]; then
    echo "🎉 所有测试通过！系统运行正常"
elif [ "$PASS_TESTS" -ge $((TOTAL_TESTS / 2)) ]; then
    echo "⚠️ 部分测试失败，请检查失败项详情"
else
    echo "❌ 多数测试失败，请执行修复方案"
fi
