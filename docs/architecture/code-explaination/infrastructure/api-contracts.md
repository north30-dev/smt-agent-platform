# API Contracts

> OpenAPI 规范文档，定义 REST API 接口契约。

**模块路径**: `api-contracts/`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/api-contracts/openapi/`

---

## 规范文件

| 文件 | 说明 |
|------|------|
| `device_api.yaml` | 设备管理 API 规范（device-service） |
| `agent_api.yaml` | Agent 服务 API 规范（全部 Agent） |

---

## device_api.yaml

定义设备管理相关接口：

- `POST /api/device` — 创建设备
- `PUT /api/device/{id}` — 更新设备
- `DELETE /api/device/{id}` — 删除设备
- `GET /api/device/{id}` — 查询设备
- `GET /api/device/list` — 分页查询
- `GET /api/device/{deviceId}/data` — 历史数据
- `GET /api/device/{deviceId}/datapoints` — 采集点列表
- `POST /api/device/{deviceId}/datapoints` — 创建采集点

---

## agent_api.yaml

定义 Agent 服务接口（19 个操作）：

**agent-knowledge (8004)**:
- `POST /v1/knowledge/upload`
- `POST /v1/knowledge/ask`
- `GET /v1/knowledge/documents`
- `DELETE /v1/knowledge/documents/{doc_id}`

**agent-maintenance (8002)**:
- `GET /v1/maintenance/health/{device_id}`
- `POST /v1/maintenance/diagnose`
- `GET /v1/maintenance/predict/{device_id}`
- `POST /v1/maintenance/cases`

**agent-quality (8003)**:
- `GET /v1/quality/monitor/{device_id}`
- `POST /v1/quality/root_cause`
- `POST /v1/quality/cases`
- `GET /v1/quality/alerts`

**agent-scheduler (8001)**:
- `POST /v1/scheduler/orders`
- `GET /v1/scheduler/orders`
- `POST /v1/scheduler/plan/generate`
- `GET /v1/scheduler/plan/current`
- `POST /v1/scheduler/urgent`

**agent-orchestrator (8005)**:
- `POST /v1/orchestrator/device_fault`
- `POST /v1/orchestrator/device_fault_event`
- `GET /v1/orchestrator/workflows/{workflow_id}`
