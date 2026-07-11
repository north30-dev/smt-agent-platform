# Python Scheduler Agent API

**版本**: v1.1 | **日期**: 2026-07-11 | **状态**: Phase 3-4

---

## 五、Python Scheduler Agent API

### 5.1 基础信息

| 项目 | 值 |
|------|-----|
| 服务名称 | agent-scheduler |
| 技术栈 | FastAPI + asyncpg + LangChain |
| 端口 | 8001 |
| 开发状态 | Phase 3 ✅ |

### 5.2 订单管理API

#### 5.2.1 查询订单列表

**端点**: `GET /v1/scheduler/orders`

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 否 | 订单状态筛选 |

**响应示例**:

```json
{
  "data": [
    {
      "order_no": "ORD-20260707-001",
      "product_type": "主板PCBA",
      "quantity": 100,
      "priority": "HIGH",
      "status": "PENDING",
      "deadline": "2026-07-08 23:49:11",
      "production_line": "LINE-1"
    }
  ],
  "total": 1
}
```

#### 5.2.2 创建订单

**端点**: `POST /v1/scheduler/orders`

**请求体**:

```json
{
  "order_no": "ORD-20260707-002",
  "product_type": "电源模块",
  "quantity": 200,
  "priority": "NORMAL",
  "deadline": "2026-07-09 12:00:00",
  "production_line": "LINE-2"
}
```

**字段约束**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| order_no | string | 是 | 订单编号（唯一） |
| product_type | string | 是 | 产品类型 |
| quantity | int | 是 | 数量 |
| priority | string | 是 | LOW/NORMAL/HIGH/URGENT |
| deadline | timestamp | 否 | 交付期限 |
| production_line | string | 否 | 产线 |

#### 5.2.3 智能排产建议

**端点**: `POST /v1/scheduler/suggest`

**请求体**:

```json
{
  "orders": ["ORD-20260707-001", "ORD-20260707-002"],
  "constraints": {
    "production_lines": ["LINE-1", "LINE-2"],
    "devices": [1, 2, 3]
  }
}
```

**响应示例**:

```json
{
  "suggestion": {
    "plan": [
      {
        "order_no": "ORD-20260707-001",
        "device_id": 1,
        "start_time": "2026-07-08 08:00",
        "end_time": "2026-07-08 12:00"
      }
    ],
    "efficiency_score": 85.5,
    "llm_explanation": "根据订单优先级和设备健康评分，建议先安排HIGH优先级订单..."
  }
}
```
