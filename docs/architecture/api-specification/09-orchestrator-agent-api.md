# Python Orchestrator Agent API

**版本**: v1.1 | **日期**: 2026-07-11 | **状态**: Phase 3-4

---

## 九、Python Orchestrator Agent API

### 9.1 基础信息

| 项目 | 值 |
|------|-----|
| 服务名称 | agent-orchestrator |
| 技术栈 | FastAPI + LangGraph |
| 端口 | 8005 |
| 依赖服务 | Scheduler (8001)、Maintenance (8002)、Quality (8003)、Knowledge (8004) |

### 9.2 多Agent编排API

#### 9.2.1 设备故障协同处理

**端点**: `POST /v1/orchestrator/device_fault`

**请求体**:

```json
{
  "device_id": 1,
  "symptom": "温度异常，振动增大"
}
```

**响应示例**:

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

#### 9.2.2 编排状态查询

**端点**: `GET /v1/orchestrator/workflow/{workflow_id}`

**响应示例**:

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
