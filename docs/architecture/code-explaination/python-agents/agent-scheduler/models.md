# agent-scheduler/models

> 调度智能体的 Pydantic 请求/响应模型。

**模块路径**: `agent-scheduler/models.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-scheduler/models.py`

---

## 类

### `OrderCreateRequest(BaseModel)`

| 字段 | 类型 | 校验 | 说明 |
|------|------|------|------|
| `order_no` | `str` | `min_length=1, max_length=64` | 工单号 |
| `product_model` | `str` | `min_length=1, max_length=64` | 产品型号 |
| `quantity` | `int` | `ge=1` | 数量 |
| `priority` | `Literal["URGENT","HIGH","NORMAL","LOW"]` | — | 优先级，默认 NORMAL |
| `delivery_date` | `str` | — | 交付日期 |
| `material_ready` | `bool` | — | 物料是否齐套，默认 False |

### `PlanAllocation(BaseModel)`

| 字段 | 类型 | 说明 |
|------|------|------|
| `order_no` | `str` | 工单号 |
| `product_model` | `str` | 产品型号 |
| `device_id` | `int` | 分配设备 ID |
| `device_name` | `str` | 分配设备名称 |
| `start_hour` | `int` | 开始小时 |
| `duration_hours` | `float` | 持续小时数 |

### `PlanResponse(BaseModel)`

| 字段 | 类型 | 说明 |
|------|------|------|
| `plan_id` | `int` | 计划 ID |
| `plan_version` | `int` | 计划版本 |
| `allocations` | `list[PlanAllocation]` | 分配列表 |
| `description` | `str` | 自然语言说明 |
| `status` | `str` | 状态 |
| `created_at` | `str` | 创建时间 |

### `UrgentRequest(BaseModel)`

| 字段 | 类型 | 说明 |
|------|------|------|
| `order_no` | `str` | 工单号 |
| `product_model` | `str` | 产品型号 |
| `quantity` | `int` | 数量 |
| `delivery_date` | `str` | 交付日期 |
| `source` | `str` | 来源，默认 "user" |

### `UrgentResponse(BaseModel)`

| 字段 | 类型 | 说明 |
|------|------|------|
| `urgent_order_no` | `str` | 急单工单号 |
| `affected_orders` | `list[AffectedOrderVO]` | 受影响订单 |
| `estimated_delay_hours` | `float` | 预计延迟小时数 |
| `adjustment_plan` | `AdjustmentPlanVO` | 调整方案 |
