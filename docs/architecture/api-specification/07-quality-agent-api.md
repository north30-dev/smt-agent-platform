# Python Quality Agent API

**版本**: v1.1 | **日期**: 2026-07-11 | **状态**: Phase 3-4

---

## 七、Python Quality Agent API

### 7.1 基础信息

| 项目 | 值 |
|------|-----|
| 服务名称 | agent-quality |
| 技术栈 | FastAPI + LangChain + asyncpg + Milvus |
| 端口 | 8003 |
| 依赖服务 | PostgreSQL (5432)、Milvus (19530)、LLM Service (1234) |

### 7.2 质量告警API

#### 7.2.1 查询质量告警

**端点**: `GET /v1/quality/alerts`

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| severity | string | 否 | 严重程度筛选 |
| status | string | 否 | 告警状态筛选 |

**响应示例**:

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

#### 7.2.2 根因分析

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

**响应示例**:

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
