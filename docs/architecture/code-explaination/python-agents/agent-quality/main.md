# agent-quality/main

> 质量分析 Agent FastAPI 应用入口。

**模块路径**: `agent-quality/main.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-quality/main.py`

---

## FastAPI 应用

```python
app = FastAPI(title="SMT 质量分析 Agent", version="0.3.0", lifespan=lifespan)
```

---

## REST 端点

### `GET /v1/quality/monitor/{device_id}` — 实时缺陷监控

**方法**: `async def monitor(device_id: int) -> MonitorResponse`

**返回值**: `MonitorResponse` — `{device_id, defect_rate, threshold, status, datapoints, analyzed_at}`

---

### `POST /v1/quality/root_cause` — 根因分析

**方法**: `async def root_cause(req: RootCauseRequest) -> RootCauseResponse`

**参数**: `{device_id, defect_description}`

**返回值**: `RootCauseResponse` — `{device_id, root_causes, corrective_actions, similar_cases}`

---

### `POST /v1/quality/cases` — 案例录入

**方法**: `async def create_case(req: CaseCreateRequest) -> CaseCreateResponse`

**参数**: `{defect_type, description, root_cause, corrective_action}`

**返回值**: `CaseCreateResponse` — `{case_id}`

---

### `GET /v1/quality/alerts` — 告警查询

**方法**: `async def list_alerts(page: int = 1, size: int | None = None) -> AlertsPageResponse`

**返回值**: `AlertsPageResponse` — `{records, total, page, size}`
