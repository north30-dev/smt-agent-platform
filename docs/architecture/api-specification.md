# SMT Agent Platform API规范文档

**版本**: v1.1
**日期**: 2026-07-11
**状态**: Phase 3-4 开发阶段
**适用范围**: 开发环境测试与集成

---

## 一、文档概述

### 1.1 目标

本文档定义了SMT智能运维平台所有服务的API规范，包括：
- Java后端服务API（设备管理）
- Python智能体层API（6个Agent）
- 大模型服务API（LM Studio）
- 中间件服务接口

### 1.2 API分层架构

```
┌─────────────────────────────────────────────────────────┐
│  交互层（Phase 4）                                       │
│  - React前端应用                                         │
│  - 用户界面与可视化                                       │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│  智能体层（Python）                                      │
│  - Orchestrator (8005) → 编排协同                        │
│  - Execution (8006)    → 执行智能体                      │
│  - Scheduler (8001)    → 生产调度                        │
│  - Maintenance (8002)  → 设备运维                        │
│  - Quality (8003)      → 质量分析                        │
│  - Knowledge (8004)    → 知识检索                        │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│  服务层（Java）                                          │
│  - Device Service (8081) → 设备台账管理                  │
│  - Gateway (8080)        → API网关路由                   │
│  - Spring Boot + MyBatis-Plus                           │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│  数据层                                                 │
│  - PostgreSQL (5432)   → 关系型数据                      │
│  - Redis (6380)        → 缓存                            │
│  - InfluxDB (8086)     → 时序数据                        │
│  - Milvus (19530)      → 向量检索                        │
│  - LM Studio (1234)    → 大模型推理                      │
└─────────────────────────────────────────────────────────┘
```

---

## 二、服务端点清单

### 2.1 应用层服务

| 服务名称 | 基础URL | 端口 | 开发状态 |
|---------|---------|------|---------|
| **Java Gateway** | `http://localhost:8080` | 8080 | Phase 1 ✅ |
| **Java Device Service** | `http://localhost:8081` | 8081 | Phase 1 ✅ |
| **Scheduler Agent** | `http://localhost:8001` | 8001 | Phase 3 ✅ |
| **Maintenance Agent** | `http://localhost:8002` | 8002 | Phase 2 ✅ |
| **Quality Agent** | `http://localhost:8003` | 8003 | Phase 3 ✅ |
| **Knowledge Agent** | `http://localhost:8004` | 8004 | Phase 2 ✅ |
| **Orchestrator Agent** | `http://localhost:8005` | 8005 | Phase 3 ✅ |
| **Execution Agent** | `http://localhost:8006` | 8006 | Phase 3 ✅ |

### 2.2 大模型服务

| 服务名称 | 基础URL | 端口 | 备注 |
|---------|---------|------|------|
| **LM Studio** | `http://192.168.116.1:1234/v1` | 1234 | 本地部署（gemma-4-e4b） |

### 2.3 中间件服务

| 服务名称 | 基础URL | 端口 | 用途 |
|---------|---------|------|------|
| **PostgreSQL** | `localhost:5432` | 5432 | 关系型数据库（smt库） |
| **Redis** | `localhost:6380` | 6380 | 缓存与会话存储 |
| **InfluxDB** | `http://localhost:8086` | 8086 | 时序数据存储 |
| **Milvus** | `localhost:19530` | 19530 | 向量检索引擎 |
| **MinIO Console** | `http://localhost:9001` | 9001 | 对象存储管理界面 |
| **Mosquitto MQTT** | `tcp://localhost:1883` | 1883 | MQTT Broker |

### 2.4 模块 Agent 文档

每个模块目录下的 `.agent/` 文件夹存放该模块的说明文档，供 Agent 在执行任务前了解模块情况、执行后记录变更。

**文档清单（共 18 个文件）**：

| 模块 | 文件1 | 文件2（特有） | 文件3 |
|------|-------|-------------|-------|
| api-contracts | MODULE_OVERVIEW.md | API_REGISTRY.md | CHANGELOG.md |
| cpp-native | MODULE_OVERVIEW.md | ALGORITHM_REGISTRY.md | CHANGELOG.md |
| docker-compose | MODULE_OVERVIEW.md | NETWORK_ENV.md | CHANGELOG.md |
| frontend | MODULE_OVERVIEW.md | PAGE_REGISTRY.md | CHANGELOG.md |
| java-backend | MODULE_OVERVIEW.md | DATABASE_SCHEMA.md | CHANGELOG.md |
| python-agents | MODULE_OVERVIEW.md | AGENT_REGISTRY.md | CHANGELOG.md |

**Agent 行为规则**：
- 执行任务前：必须阅读模块 `.agent/MODULE_OVERVIEW.md`
- 执行任务后：必须更新 `.agent/CHANGELOG.md`
- 详见 AGENTS.md §7「模块 Agent 文档规范」

---

## 三、Java Device Service API

### 3.1 基础信息

- **服务名称**: smt-device-service
- **技术栈**: Spring Boot 3.x + MyBatis-Plus
- **认证方式**: JWT Token（开发环境使用固定凭据）
- **API路径前缀**: `/api/device`（单数形式，不是复数）

### 3.2 认证API

#### 3.2.1 用户登录

**端点**: `POST /api/auth/login`

**请求体**:
```json
{
  "username": "admin",
  "password": "dev-only-admin"
}
```

**响应示例**（成功）:
```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expireTime": "2026-07-08 01:00:00"
  }
}
```

**开发环境凭据**:
- Username: `admin`
- Password: `dev-only-admin`
- 生产环境密码: `admindev`（见docker-compose/.env）

**Token使用**:
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

### 3.3 设备管理API

#### 3.3.1 查询设备列表（分页）

**端点**: `GET /api/device/list`

**查询参数**:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | int | 否 | 1 | 页码 |
| size | int | 否 | 10 | 每页数量 |
| productionLine | string | 否 | - | 产线筛选 |
| deviceType | string | 否 | - | 设备类型筛选 |
| status | string | 否 | - | 设备状态筛选 |

**请求示例**:
```http
GET /api/device/list?page=1&size=10&productionLine=LINE-1
```

**响应示例**:
```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "records": [
      {
        "id": 1,
        "deviceCode": "DEV-001",
        "deviceName": "贴片机A",
        "deviceType": "贴片机",
        "productionLine": "LINE-1",
        "ipAddress": "192.168.1.101",
        "protocolType": "MQTT",
        "opcUaEndpoint": null,
        "status": "RUNNING",
        "healthScore": 95,
        "createTime": "2026-07-07 23:49:11",
        "updateTime": "2026-07-07 23:49:11",
        "createBy": "system",
        "updateBy": "system",
        "deleted": 0
      }
    ],
    "total": 1,
    "size": 10,
    "current": 1,
    "pages": 1
  }
}
```

---

#### 3.3.2 查询设备详情

**端点**: `GET /api/device/{id}`

**路径参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | long | 是 | 设备ID |

**请求示例**:
```http
GET /api/device/1
```

**响应示例**（成功）:
```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "id": 1,
    "deviceCode": "DEV-001",
    "deviceName": "贴片机A",
    "deviceType": "贴片机",
    "productionLine": "LINE-1",
    "ipAddress": "192.168.1.101",
    "protocolType": "MQTT",
    "status": "RUNNING",
    "healthScore": 95,
    "createTime": "2026-07-07 23:49:11",
    "updateTime": "2026-07-07 23:49:11"
  }
}
```

**响应示例**（设备不存在）:
```json
{
  "code": 404,
  "message": "设备不存在",
  "data": null
}
```

---

#### 3.3.3 创建设备

**端点**: `POST /api/device`

**认证要求**: 需JWT Token

**请求体**:
```json
{
  "deviceCode": "DEV-002",
  "deviceName": "回流焊炉B",
  "deviceType": "回流焊炉",
  "productionLine": "LINE-1",
  "ipAddress": "192.168.1.102",
  "protocolType": "OPC_UA",
  "opcUaEndpoint": "opc.tcp://192.168.1.102:4840",
  "status": "IDLE",
  "healthScore": 100
}
```

**字段约束**:
| 字段 | 类型 | 必填 | 约束 | 说明 |
|------|------|------|------|------|
| deviceCode | string(64) | 是 | 唯一 | 设备编码 |
| deviceName | string(128) | 是 | - | 设备名称 |
| deviceType | string(32) | 否 | - | 设备类型 |
| productionLine | string(32) | 否 | - | 产线 |
| ipAddress | string(64) | 否 | - | IP地址 |
| protocolType | string(16) | 否 | MQTT/OPC_UA | 协议类型 |
| opcUaEndpoint | string(256) | 否 | - | OPC UA端点 |
| status | string(16) | 否 | 默认RUNNING | 设备状态 |
| healthScore | int | 否 | 默认100，范围0-100 | 健康评分 |

**响应示例**:
```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "id": 2,
    "deviceCode": "DEV-002",
    "deviceName": "回流焊炉B",
    ...
  }
}
```

---

#### 3.3.4 更新设备

**端点**: `PUT /api/device/{id}`

**认证要求**: 需JWT Token

**路径参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | long | 是 | 设备ID |

**请求体**（部分字段更新）:
```json
{
  "deviceName": "回流焊炉B-更新",
  "status": "MAINTENANCE",
  "healthScore": 85
}
```

**注意**: `deviceCode`字段不可更新（唯一约束）

**响应示例**:
```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "id": 2,
    "deviceCode": "DEV-002",
    "deviceName": "回流焊炉B-更新",
    "status": "MAINTENANCE",
    "healthScore": 85,
    ...
  }
}
```

---

#### 3.3.5 删除设备

**端点**: `DELETE /api/device/{id}`

**认证要求**: 需JWT Token

**删除方式**: 软删除（设置deleted=1，不物理删除）

**请求示例**:
```http
DELETE /api/device/2
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**响应示例**:
```json
{
  "code": 200,
  "message": "操作成功",
  "data": null
}
```

---

### 3.4 健康检查API

#### 3.4.1 Spring Boot Actuator

**端点**: `GET /actuator/health`

**响应示例**:
```json
{
  "status": "UP",
  "components": {
    "db": {"status": "UP"},
    "redis": {"status": "UP"},
    "diskSpace": {"status": "UP"}
  }
}
```

#### 3.4.2 Actuator端点列表

**端点**: `GET /actuator`

**响应示例**:
```json
{
  "_links": {
    "self": {"href": "http://localhost:8081/actuator"},
    "health": {"href": "http://localhost:8081/actuator/health"},
    "prometheus": {"href": "http://localhost:8081/actuator/prometheus"},
    ...
  }
}
```

---

### 3.5 错误处理规范

**标准错误响应格式**:
```json
{
  "code": 500,
  "message": "系统内部错误",
  "data": null
}
```

**错误码定义**:
| 错误码 | 说明 | HTTP状态码 |
|--------|------|-----------|
| 200 | 操作成功 | 200 |
| 400 | 参数校验失败 | 400 |
| 401 | 认证失败 | 401 |
| 403 | 权限不足 | 403 |
| 404 | 资源不存在 | 404 |
| 500 | 系统内部错误 | 500 |

---

## 四、Python Scheduler Agent API

### 4.1 基础信息

- **服务名称**: agent-scheduler
- **技术栈**: FastAPI + asyncpg + LangChain
- **端口**: 8001
- **开发状态**: Phase 3（⚠️ 字段映射错误待修复）

### 4.2 订单管理API

#### 4.2.1 查询订单列表

**端点**: `GET /v1/scheduler/orders`

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 否 | 订单状态筛选 |

**响应示例**（⚠️ 当前有字段错误）:
```json
{
  "error": "internal_error",
  "message": "内部错误"
}
```

**预期响应**（修复后）:
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

---

#### 4.2.2 创建订单

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

**响应示例**（预期）:
```json
{
  "order_id": "ORD-20260707-002",
  "message": "订单创建成功"
}
```

---

#### 4.2.3 智能排产建议

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

**响应示例**（预期）:
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

---

## 五、Python Maintenance Agent API

### 5.1 基础信息

- **服务名称**: agent-maintenance
- **技术栈**: FastAPI + LangChain + httpx
- **端口**: 8002
- **依赖服务**: Java device-service (8081)、LM Studio (1234)

### 5.2 设备健康分析API

#### 5.2.1 设备健康诊断

**端点**: `GET /v1/maintenance/health/{device_id}`

**路径参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | int | 是 | 设备ID |

**请求示例**:
```http
GET /v1/maintenance/health/1
```

**响应示例**（⚠️ 当前依赖Java数据）:
```json
{
  "error": "device_service_unavailable",
  "message": "Client error '404 ' for url 'http://localhost:8081/api/device/1'"
}
```

**预期响应**（修复后）:
```json
{
  "device_id": 1,
  "device_name": "贴片机A",
  "health_score": 95,
  "status": "健康",
  "analysis": {
    "overall_condition": "良好",
    "risk_factors": [],
    "recommendations": [
      "设备运行正常，建议保持当前维护频率",
      "建议定期检查吸嘴磨损情况"
    ]
  },
  "llm_insights": "根据设备历史运行数据和当前健康评分，该设备整体运行稳定..."
}
```

---

#### 5.2.2 设备故障诊断

**端点**: `POST /v1/maintenance/diagnose`

**请求体**:
```json
{
  "device_id": 1,
  "symptom": "温度异常，振动增大",
  "context": {
    "running_hours": 1200,
    "last_maintenance": "2026-06-01"
  }
}
```

**响应示例**（预期）:
```json
{
  "device_id": 1,
  "diagnosis": {
    "possible_causes": [
      {
        "cause": "轴承磨损",
        "probability": 0.75,
        "reasoning": "振动增大通常由轴承磨损引起"
      },
      {
        "cause": "温度传感器故障",
        "probability": 0.25,
        "reasoning": "温度异常可能是传感器误报"
      }
    ],
    "recommended_actions": [
      "检查轴承磨损情况",
      "校准温度传感器",
      "安排停机维护"
    ]
  },
  "llm_analysis": "根据症状描述和历史维护记录，建议优先检查轴承..."
}
```

---

## 六、Python Quality Agent API

### 6.1 基础信息

- **服务名称**: agent-quality
- **技术栈**: FastAPI + LangChain + asyncpg + Milvus
- **端口**: 8003
- **依赖服务**: PostgreSQL (5432)、Milvus (19530)、LM Studio (1234)

### 6.2 质量告警API

#### 6.2.1 查询质量告警

**端点**: `GET /v1/quality/alerts`

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| severity | string | 否 | 严重程度筛选 |
| status | string | 否 | 告警状态筛选 |

**响应示例**（⚠️ 当前有字段错误）:
```json
{
  "error": "internal_error",
  "message": "内部错误"
}
```

**预期响应**（修复后）:
```json
{
  "data": [
    {
      "alert_no": "QA-20260707-001",
      "device_id": 3,
      "alert_type": "AOI_DEFECT",
      "severity": "MEDIUM",
      "defect_rate": 2.5,
      "threshold": 1.0,
      "message": "AOI检测不良率超标",
      "status": "OPEN",
      "create_time": "2026-07-07 23:49:11"
    }
  ],
  "total": 1
}
```

---

#### 6.2.2 根因分析

**端点**: `POST /v1/quality/root_cause`

**请求体**:
```json
{
  "device_id": 1,
  "defect_description": "AOI检测不良率超标",
  "context": {
    "defect_rate": 2.5,
    "threshold": 1.0,
    "production_line": "LINE-1"
  }
}
```

**响应示例**（预期）:
```json
{
  "root_cause": {
    "primary_cause": "吸嘴磨损导致元件偏移",
    "contributing_factors": [
      "PCB板翘曲",
      "温度曲线参数偏差"
    ],
    "analysis_method": "人机料法环分析 + 历史案例检索"
  },
  "corrective_actions": [
    {
      "action": "更换吸嘴",
      "priority": "HIGH",
      "estimated_effect": "降低不良率至0.8%"
    },
    {
      "action": "调整PCB支撑",
      "priority": "MEDIUM",
      "estimated_effect": "改善元件贴装精度"
    }
  ],
  "similar_cases": [
    {
      "case_no": "QC-001",
      "similarity_score": 0.85,
      "description": "贴片机元件偏移案例"
    }
  ],
  "llm_explanation": "根据历史案例库检索和人机料法环分析..."
}
```

---

## 七、Python Knowledge Agent API

### 7.1 基础信息

- **服务名称**: agent-knowledge
- **技术栈**: FastAPI + LangChain + Milvus
- **端口**: 8004
- **依赖服务**: Milvus (19530)、LM Studio (1234)

### 7.2 知识检索API

#### 7.2.1 知识问答

**端点**: `POST /v1/knowledge/query`

**请求体**:
```json
{
  "question": "贴片机元件偏移如何处理？",
  "context": {
    "device_type": "贴片机",
    "defect_type": "元件偏移"
  }
}
```

**响应示例**（预期）:
```json
{
  "answer": "贴片机元件偏移通常由以下原因引起：1. 吸嘴磨损...",
  "sources": [
    {
      "case_no": "QC-001",
      "title": "贴片机元件偏移处理案例",
      "relevance_score": 0.92
    }
  ],
  "llm_response": "根据知识库检索和历史案例分析，建议..."
}
```

---

#### 7.2.2 历史案例检索

**端点**: `POST /v1/knowledge/cases/search`

**请求体**:
```json
{
  "query": "温度异常导致焊接不良",
  "filters": {
    "device_type": "回流焊炉",
    "defect_type": "焊接不良"
  },
  "top_k": 5
}
```

**响应示例**（预期）:
```json
{
  "cases": [
    {
      "case_no": "QC-002",
      "device_type": "回流焊炉",
      "defect_type": "焊接不良",
      "symptom_description": "焊点虚焊或冷焊",
      "root_cause_analysis": "温度曲线参数不合适...",
      "corrective_actions": "优化温度曲线...",
      "effectiveness_score": 90.0,
      "relevance_score": 0.88
    }
  ],
  "total": 1
}
```

---

## 八、Python Orchestrator Agent API

### 8.1 基础信息

- **服务名称**: agent-orchestrator
- **技术栈**: FastAPI + LangGraph
- **端口**: 8005
- **依赖服务**: Scheduler (8001)、Maintenance (8002)、Quality (8003)、Knowledge (8004)

### 8.2 多Agent编排API

#### 8.2.1 设备故障协同处理

**端点**: `POST /v1/orchestrator/device_fault`

**请求体**:
```json
{
  "device_id": 1,
  "symptom": "温度异常，振动增大"
}
```

**响应示例**（预期）:
```json
{
  "workflow_id": "WF-20260707-001",
  "status": "RUNNING",
  "steps": [
    {
      "agent": "maintenance",
      "action": "diagnose",
      "result": {
        "diagnosis": "轴承磨损",
        "recommendations": ["更换轴承"]
      }
    },
    {
      "agent": "quality",
      "action": "analyze_impact",
      "result": {
        "affected_orders": ["ORD-20260707-001"],
        "quality_risk": "HIGH"
      }
    },
    {
      "agent": "scheduler",
      "action": "reschedule",
      "result": {
        "new_plan": "调整订单至备用设备",
        "efficiency_impact": -5.2
      }
    }
  ],
  "summary": {
    "root_cause": "轴承磨损导致设备异常",
    "corrective_actions": ["更换轴承", "调整生产计划"],
    "estimated_recovery_time": "2小时"
  }
}
```

---

#### 8.2.2 编排状态查询

**端点**: `GET /v1/orchestrator/workflow/{workflow_id}`

**响应示例**（预期）:
```json
{
  "workflow_id": "WF-20260707-001",
  "status": "COMPLETED",
  "start_time": "2026-07-07 23:50:00",
  "end_time": "2026-07-07 23:52:30",
  "agents_involved": ["maintenance", "quality", "scheduler"],
  "result": {
    "success": true,
    "message": "设备故障已处理，生产计划已调整"
  }
}
```

---

## 八-B、Python Execution Agent API

### 8B.1 基础信息

- **服务名称**: agent-execution
- **技术栈**: FastAPI + SQLAlchemy
- **端口**: 8006
- **依赖服务**: PostgreSQL (5432)

### 8B.2 执行管理API

#### 8B.2.1 创建执行指令

**端点**: `POST /api/agent/execution/command`

**请求体**:
```json
{
  "command_type": "MAINTENANCE",
  "target_device_id": 1,
  "description": "更换轴承",
  "priority": "HIGH",
  "assigned_to": "维修组A"
}
```

**响应示例**:
```json
{
  "command_id": "CMD-20260711-001",
  "status": "PENDING",
  "message": "指令创建成功"
}
```

---

#### 8B.2.2 审批执行指令

**端点**: `POST /api/agent/execution/approve`

**请求体**:
```json
{
  "command_id": "CMD-20260711-001",
  "approved": true,
  "approver": "张工",
  "comment": "同意执行"
}
```

---

#### 8B.2.3 上报执行进度

**端点**: `POST /api/agent/execution/progress`

**请求体**:
```json
{
  "command_id": "CMD-20260711-001",
  "progress_percent": 50,
  "status": "IN_PROGRESS",
  "remark": "轴承已拆卸，准备安装新件"
}
```

---

## 九、LM Studio API

### 9.1 基础信息

- **服务名称**: LM Studio（本地部署）
- **技术栈**: OpenAI兼容API
- **端口**: 1234
- **当前模型**: google/gemma-4-e4b

### 9.2 大模型调用API

#### 9.2.1 获取模型列表

**端点**: `GET /v1/models`

**认证**: Bearer Token

**请求示例**:
```http
GET http://192.168.116.1:1234/v1/models
Authorization: Bearer sk-lm-dbMlwJNn:IJyAOrh0mrvZ6eeJJ2OA
```

**响应示例**:
```json
{
  "data": [
    {
      "id": "google/gemma-4-e4b",
      "object": "model",
      "owned_by": "google"
    }
  ]
}
```

---

#### 9.2.2 对话补全

**端点**: `POST /v1/chat/completions`

**认证**: Bearer Token

**请求体**:
```json
{
  "model": "google/gemma-4-e4b",
  "messages": [
    {
      "role": "user",
      "content": "分析贴片机元件偏移的可能原因"
    }
  ],
  "temperature": 0.7,
  "max_tokens": 1000
}
```

**响应示例**:
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "贴片机元件偏移可能由以下原因引起：1. 吸嘴磨损..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 120,
    "total_tokens": 135
  }
}
```

---

## 十、中间件服务接口

### 10.1 PostgreSQL

**连接信息**:
```
Host: localhost (docker: smt-postgres)
Port: 5432
Database: smt
User: smt
Password: smt123
```

**关键表结构**:
| 表名 | 用途 | 关键字段 |
|------|------|---------|
| device | 设备台账 | device_code, device_name, health_score |
| production_orders | 订单数据 | order_no, priority, status |
| quality_alerts | 质量告警 | alert_no, severity, defect_rate |

---

### 10.2 Redis

**连接信息**:
```
Host: localhost (docker: smt-redis)
Port: 6380
Password: root
```

**用途**:
- 会话存储
- 缓存设备数据
- Agent状态缓存

---

### 10.3 InfluxDB

**连接信息**:
```
Host: http://localhost:8086
Org: smt
Bucket: device_data
Token: devtoken123
```

**用途**:
- 设备时序数据存储
- 温度、振动等传感器数据
- 健康评分历史记录

---

### 10.4 Milvus

**连接信息**:
```
Host: localhost (docker: smt-milvus)
Port: 19530
```

**用途**:
- 知识案例向量检索
- 历史案例相似度匹配
- RAG知识库

---

## 十一、API调用链路示例

### 11.1 设备故障处理完整链路

```bash
# 1. 用户触发故障处理
curl -X POST http://localhost:8005/v1/orchestrator/device_fault \
  -H "Content-Type: application/json" \
  -d '{"device_id":1,"symptom":"温度异常"}'

# 2. Orchestrator调用Maintenance诊断
curl -X POST http://localhost:8002/v1/maintenance/diagnose \
  -H "Content-Type: application/json" \
  -d '{"device_id":1,"symptom":"温度异常"}'

# 3. Maintenance查询Java设备信息
curl http://localhost:8081/api/device/1

# 4. Maintenance调用LM Studio推理
curl -X POST http://192.168.116.1:1234/v1/chat/completions \
  -H "Authorization: Bearer sk-lm-dbMlwJNn:IJyAOrh0mrvZ6eeJJ2OA" \
  -H "Content-Type: application/json" \
  -d '{"model":"google/gemma-4-e4b","messages":[{"role":"user","content":"分析设备温度异常原因"}]}'

# 5. Orchestrator调用Quality分析影响
curl -X POST http://localhost:8003/v1/quality/root_cause \
  -H "Content-Type: application/json" \
  -d '{"device_id":1,"defect_description":"设备异常可能导致质量问题"}'

# 6. Quality调用Knowledge检索历史案例
curl -X POST http://localhost:8004/v1/knowledge/cases/search \
  -H "Content-Type: application/json" \
  -d '{"query":"温度异常导致焊接不良","top_k":5}'

# 7. Orchestrator调用Scheduler调整计划
curl -X POST http://localhost:8001/v1/scheduler/suggest \
  -H "Content-Type: application/json" \
  -d '{"orders":["ORD-20260707-001"],"constraints":{"production_lines":["LINE-1"]}}'

# 8. 创建执行指令
curl -X POST http://localhost:8006/api/agent/execution/command \
  -H "Content-Type: application/json" \
  -d '{"command_type":"MAINTENANCE","target_device_id":1,"description":"更换轴承","priority":"HIGH"}'
```

---

## 十二、开发状态与已知问题

### 12.1 已完成功能（Phase 1-3）

| 服务 | 功能 | 状态 |
|------|------|------|
| Java Gateway | API网关路由 | ✅ 完成 |
| Java device-service | 设备CRUD + 健康检查 | ✅ 完成 |
| Scheduler Agent | 订单管理 + 排产建议 | ✅ 完成 |
| Maintenance Agent | 设备健康诊断 + 故障诊断 | ✅ 完成 |
| Quality Agent | 质量告警 + 根因分析 | ✅ 完成 |
| Knowledge Agent | 知识检索 + RAG问答 | ✅ 完成 |
| Orchestrator Agent | 多Agent编排 | ✅ 完成 |
| Execution Agent | 执行指令管理 | ✅ 完成 |
| LM Studio集成 | OpenAI兼容API | ✅ 完成 |
| 模块Agent文档 | 18个文档文件 | ✅ 完成 |

### 12.2 开发中功能（Phase 4）

| 服务 | 功能 | 说明 |
|------|------|------|
| Frontend | React前端界面 | 页面开发中 |
| C++ Native | 高性能算法库 | 待开发 |

---

## 十三、附录

### 13.1 API测试脚本

**位置**: `scripts/api_integration_test.sh`

```bash
bash scripts/api_integration_test.sh
```

### 13.2 数据库初始化脚本

**位置**: `.trae/repair-docs/phase3_tables.sql`

**执行方式**:
```bash
docker exec -i smt-postgres psql -U smt -d smt < .trae/repair-docs/phase3_tables.sql
```

### 13.3 服务重启命令

**中间件重启**:
```bash
cd docker-compose
docker compose up -d
```

**应用层重启**:
```bash
# Java
cd java-backend
mvn -pl smt-device-service spring-boot:run

# Python Agents
cd python-agents
uv run uvicorn agent-scheduler.main:app --port 8001 &
uv run uvicorn agent-maintenance.main:app --port 8002 &
uv run uvicorn agent-quality.main:app --port 8003 &
uv run uvicorn agent-knowledge.main:app --port 8004 &
uv run uvicorn agent-orchestrator.main:app --port 8005 &
uv run uvicorn agent-execution.main:app --port 8006 &
```


---

**文档版本**: v1.1
**最后更新**: 2026-07-11
**维护者**: SMT Platform Team
**状态**: Phase 3-4 开发中