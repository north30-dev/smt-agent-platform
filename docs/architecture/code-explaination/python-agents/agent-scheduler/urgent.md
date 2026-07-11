# agent-scheduler/urgent

> 急单插单响应模块，分析影响并生成调整方案。

**模块路径**: `agent-scheduler/urgent.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-scheduler/urgent.py`

---

## 顶层函数

### `async handle_urgent(req) -> dict`

> 处理急单插单

**签名**: `async def handle_urgent(req) -> dict`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `req` | `UrgentRequest` | 急单请求 |

**返回值**: `dict` — UrgentResponse 格式

**逻辑**:
1. 录入急单（priority=URGENT, material_ready=True）
2. 获取当前 ACTIVE 计划；无计划则返回"可直接排入"
3. 估算 duration，查找受影响订单
4. 调用 LLM 生成调整方案（换线建议/加班建议）
5. 返回 `{affected_orders, estimated_delay_hours, adjustment_plan}`

---

### `_find_affected_orders(allocations, urgent_duration) -> list[dict]`

> 查找受影响订单

**签名**: `def _find_affected_orders(allocations, urgent_duration) -> list[dict]`

**逻辑**: 启发式：若分配的 start_hour < urgent_duration，则视为受影响

---

### `_parse_adjustment_plan(raw_text: str) -> dict`

> 解析 LLM 调整方案

**返回值**: `dict` — `{changeover_suggestion, overtime_suggestion}`
