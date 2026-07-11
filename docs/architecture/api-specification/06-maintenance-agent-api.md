# Python Maintenance Agent API

**版本**: v1.1 | **日期**: 2026-07-11 | **状态**: Phase 3-4

---

## 六、Python Maintenance Agent API

### 6.1 基础信息

| 项目 | 值 |
|------|-----|
| 服务名称 | agent-maintenance |
| 技术栈 | FastAPI + LangChain + httpx |
| 端口 | 8002 |
| 依赖服务 | Java device-service (8081)、LLM Service (1234) |

### 6.2 设备健康分析API

#### 6.2.1 设备健康诊断

**端点**: `GET /v1/maintenance/health/{device_id}`

**路径参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | int | 是 | 设备ID |

**响应示例**:

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

#### 6.2.2 设备故障诊断

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

**响应示例**:

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
