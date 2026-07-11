# agent-scheduler/order_store

> 订单与排产计划 PostgreSQL 存储。

**模块路径**: `agent-scheduler/order_store.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-scheduler/order_store.py`

---

## 顶层函数

### `async save_order(order_no, product_model, quantity, priority, delivery_date, material_ready, source="user") -> int`

> 保存订单

**返回值**: `int` — 订单 ID

---

### `async list_orders(status: str | None = None) -> list[dict]`

> 查询订单列表

**排序**: 按 `delivery_date ASC`

---

### `async update_order_status(order_id: int, status: str) -> None`

> 更新订单状态

---

### `async save_plan(allocations, description, plan_version) -> int`

> 保存排产计划（事务性归档旧 ACTIVE 计划）

**返回值**: `int` — 计划 ID

---

### `async get_current_plan() -> dict | None`

> 获取当前 ACTIVE 计划

---

### `async get_next_plan_version() -> int`

> 获取下一个计划版本号
