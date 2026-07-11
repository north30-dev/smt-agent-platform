# agent-orchestrator/main

> agent-orchestrator FastAPI 应用入口。

**模块路径**: `agent-orchestrator/main.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-orchestrator/main.py`

---

## FastAPI 应用

```python
app = FastAPI(title="SMT Agent 编排服务", version="0.3.0", lifespan=lifespan)
```

---

## 生命周期

- **Startup**: `await init_workflow_table()`（幂等建表）
- **Shutdown**: 关闭 `llm_client`、`agent_clients`、PG 连接池

---

## REST 端点

### `POST /v1/orchestrator/device_fault` — 设备故障编排

**方法**: `async def device_fault(req: DeviceFaultRequest) -> WorkflowResponse`

**参数**: `{device_id, symptom}`

**返回值**: `WorkflowResponse` — `{workflow_id, status, diagnosis, quality_assessment, schedule_adjustment, instructions, summary, errors}`

---

### `POST /v1/orchestrator/device_fault_event` — 事件驱动编排

**方法**: `async def device_fault_event(req: DeviceFaultEventRequest) -> WorkflowResponse`

**参数**: `{device_id, symptom, source}`

---

### `GET /v1/orchestrator/workflows/{workflow_id}` — 查询工作流

**方法**: `async def get_workflow(workflow_id: str) -> WorkflowResponse`

**返回值**: `WorkflowResponse` — 从 PostgreSQL 查询，不存在返回 404

---

## 内部函数

### `_determine_status(result: dict) -> str`

> 判断工作流状态

**逻辑**: 统计成功节点数 → 0 errors + 3 successes → "SUCCESS" → 0 successes → "FAILED" → 否则 "PARTIAL"

### `async _run_device_fault_workflow(device_id: int, symptom: str) -> WorkflowResponse`

> 执行编排工作流

**逻辑**: 生成 workflow_id → 构建初始状态 → `app_graph.ainvoke` → 判断状态 → 持久化到 PG → 返回 WorkflowResponse
