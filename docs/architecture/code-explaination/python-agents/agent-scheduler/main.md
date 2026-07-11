# agent-scheduler/main

> 调度智能体 FastAPI 应用入口。

**模块路径**: `agent-scheduler/main.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-scheduler/main.py`

---

## REST 端点

### `POST /v1/scheduler/orders` — 录入订单

**方法**: `async def create_order(req: OrderCreateRequest) -> OrderResponse`

**返回值**: `OrderResponse` — `{order_id, order_no, product_model, quantity, priority, delivery_date, material_ready, status, created_at}`

---

### `GET /v1/scheduler/orders` — 查询订单列表

**方法**: `async def list_orders(status: str | None = None) -> OrderListResponse`

**返回值**: `OrderListResponse` — `{records, total}`

---

### `POST /v1/scheduler/plan/generate` — 生成排产计划

**方法**: `async def generate_plan(req: PlanGenerateRequest) -> PlanResponse`

**返回值**: `PlanResponse` — `{plan_id, plan_version, allocations, description, status, created_at}`

---

### `GET /v1/scheduler/plan/current` — 查询当前排产计划

**方法**: `async def get_current_plan() -> PlanResponse`

**返回值**: `PlanResponse` — 当前 ACTIVE 计划，不存在返回 404

---

### `POST /v1/scheduler/urgent` — 急单插单

**方法**: `async def handle_urgent(req: UrgentRequest) -> UrgentResponse`

**返回值**: `UrgentResponse` — `{urgent_order_no, affected_orders, estimated_delay_hours, adjustment_plan}`
