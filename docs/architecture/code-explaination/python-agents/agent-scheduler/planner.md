# agent-scheduler/planner

> 排产计划生成模块，基于订单优先级 + 交付日期 + 物料齐套 + 设备状态。

**模块路径**: `agent-scheduler/planner.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-scheduler/planner.py`

---

## 模块级常量

| 名称 | 类型 | 说明 |
|------|------|------|
| `_PRIORITY_ORDER` | `dict` | `{"URGENT": 0, "HIGH": 1, "NORMAL": 2, "LOW": 3}` |

---

## 顶层函数

### `async generate_plan() -> dict`

> 生成排产计划

**签名**: `async def generate_plan() -> dict`

**返回值**: `dict` — PlanResponse 格式

**排产规则**:
1. 仅处理 status=PENDING 且 material_ready=True 的订单
2. 仅分配 status=RUNNING 且 healthScore ≥ 阈值的设备
3. 排序：URGENT 优先 → delivery_date 升序 → quantity 降序
4. 分配：按可用设备数轮询分配（round-robin）

**逻辑**:
1. 获取 PENDING 订单 → 过滤 material_ready
2. 获取 RUNNING 设备 → 过滤 healthScore
3. 排序订单
4. Round-robin 分配
5. 调用 LLM 生成自然语言说明
6. 保存计划到 DB，归档旧计划
7. 更新已分配订单状态为 PLANNED

---

### `_round_robin_allocate(orders, devices) -> list[dict]`

> 轮询分配算法

**签名**: `def _round_robin_allocate(orders, devices) -> list[dict]`

**返回值**: `list[dict]` — 分配列表 `[{order_id, order_no, product_model, device_id, device_name, start_hour, duration_hours}]`

**逻辑**: 维护每个设备的 start_hour 游标 → 按顺序分配 → duration = ceil(quantity/capacity) + changeover_hours
