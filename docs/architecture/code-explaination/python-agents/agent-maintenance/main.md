# agent-maintenance/main

> 设备运维 Agent FastAPI 应用入口，提供健康评估、故障诊断、预测性维护、案例录入四个接口。

**模块路径**: `agent-maintenance/main.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-maintenance/main.py`

---

## FastAPI 应用

```python
app = FastAPI(title="SMT 设备运维 Agent", version="0.2.0", lifespan=lifespan)
```

---

## REST 端点

### `GET /v1/maintenance/health/{device_id}` — 设备健康评估

**方法**: `async def health(device_id: int) -> HealthResponse`

**参数**:

| 参数 | 类型 | 位置 | 说明 |
|------|------|------|------|
| `device_id` | `int` | Path | 设备 ID |

**返回值**: `HealthResponse` — `{device_id, health_score, status, risk_level, analysis}`

**逻辑**: 获取设备 → 解析 healthScore → 计算 risk_level（≥85 LOW, ≥60 MEDIUM, else HIGH）

---

### `POST /v1/maintenance/diagnose` — 故障诊断

**方法**: `async def diagnose(req: DiagnoseRequest) -> DiagnoseResponse`

**参数**:

| 参数 | 类型 | 位置 | 说明 |
|------|------|------|------|
| `req` | `DiagnoseRequest` | Body | `{device_id, symptom}` |

**返回值**: `DiagnoseResponse` — `{root_causes, repair_suggestions, similar_cases}`

---

### `GET /v1/maintenance/predict/{device_id}` — 预测性维护

**方法**: `async def predict(device_id: int) -> PredictResponse`

**参数**:

| 参数 | 类型 | 位置 | 说明 |
|------|------|------|------|
| `device_id` | `int` | Path | 设备 ID |

**返回值**: `PredictResponse` — `{trend, threshold_alerts, forecast, recommendation, data_sufficient}`

---

### `POST /v1/maintenance/cases` — 故障案例录入

**方法**: `async def create_case(req: CaseCreateRequest) -> CaseCreateResponse`

**参数**:

| 参数 | 类型 | 位置 | 说明 |
|------|------|------|------|
| `req` | `CaseCreateRequest` | Body | `{device_type, symptom, root_cause, solution}` |

**返回值**: `CaseCreateResponse` — `{case_id}`

---

## 全局异常处理

| 异常类型 | HTTP 状态码 | 说明 |
|---------|------------|------|
| `DeviceServiceUnavailable` | 503 | 设备服务不可用 |
| `LLMClientError` | 503 | 大模型服务不可用 |
| `VectorStoreError` | 503 | 向量库不可用 |
| `ValueError` | 400 | 参数错误 |
| `Exception` | 500 | 内部错误 |
