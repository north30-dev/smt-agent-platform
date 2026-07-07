"""调度智能体的 Pydantic 请求/响应模型。

字段命名统一 snake_case，与 OpenAPI 契约对齐。
"""

from typing import Literal

from pydantic import BaseModel, Field


class OrderCreateRequest(BaseModel):
    """订单录入请求体。"""

    order_no: str = Field(..., min_length=1, max_length=64, description="订单编号")
    product_model: str = Field(..., min_length=1, max_length=64, description="产品型号")
    quantity: int = Field(..., ge=1, description="订单数量")
    priority: Literal["URGENT", "HIGH", "NORMAL", "LOW"] = Field(
        "NORMAL", description="优先级：URGENT / HIGH / NORMAL / LOW"
    )
    delivery_date: str = Field(..., description="交付日期（ISO 日期 YYYY-MM-DD）")
    material_ready: bool = Field(False, description="物料是否齐套")


class OrderResponse(BaseModel):
    """订单响应。"""

    order_id: int = Field(..., description="订单 ID")
    order_no: str = Field(..., description="订单编号")
    product_model: str = Field(..., description="产品型号")
    quantity: int = Field(..., description="订单数量")
    priority: str = Field(..., description="优先级")
    delivery_date: str = Field(..., description="交付日期")
    material_ready: bool = Field(..., description="物料是否齐套")
    status: str = Field(..., description="订单状态")
    created_at: str = Field(..., description="创建时间")


class OrderListResponse(BaseModel):
    """订单列表响应。"""

    records: list[OrderResponse] = Field(..., description="订单列表")
    total: int = Field(..., description="订单总数")


class PlanGenerateRequest(BaseModel):
    """排产计划生成请求体（无必填字段，可选强制重新生成）。"""

    force_regenerate: bool = Field(
        False, description="是否强制重新生成（即使已有 ACTIVE 计划）"
    )


class PlanAllocation(BaseModel):
    """排产计划中的单条分配项。"""

    order_no: str = Field(..., description="订单编号")
    product_model: str = Field(..., description="产品型号")
    device_id: int = Field(..., description="设备 ID")
    device_name: str = Field(..., description="设备名称")
    start_hour: int = Field(..., description="相对当前时刻的小时偏移")
    duration_hours: float = Field(..., description="占用时长（小时）")


class PlanResponse(BaseModel):
    """排产计划响应。"""

    plan_id: int = Field(..., description="计划 ID")
    plan_version: int = Field(..., description="计划版本号")
    allocations: list[PlanAllocation] = Field(..., description="订单-设备-时段分配")
    description: str = Field(..., description="排产说明（LLM 生成）")
    status: str = Field(..., description="计划状态")
    created_at: str = Field(..., description="创建时间")


class UrgentRequest(BaseModel):
    """急单插单请求体。"""

    order_no: str = Field(..., min_length=1, max_length=64, description="急单编号")
    product_model: str = Field(..., min_length=1, max_length=64, description="产品型号")
    quantity: int = Field(..., ge=1, description="订单数量")
    delivery_date: str = Field(..., description="交付日期（ISO 日期 YYYY-MM-DD）")
    source: str = Field("user", description="订单来源（user/orchestrator_synthetic）")


class AffectedOrderVO(BaseModel):
    """受急单影响的订单。"""

    order_no: str = Field(..., description="受影响订单编号")
    product_model: str = Field(..., description="产品型号")
    delay_hours: float = Field(..., description="预计延迟小时数")


class AdjustmentPlanVO(BaseModel):
    """急单调整方案。"""

    changeover_suggestion: str = Field(..., description="换线建议")
    overtime_suggestion: str = Field(..., description="加班建议")


class UrgentResponse(BaseModel):
    """急单插单响应。"""

    urgent_order_no: str = Field(..., description="急单编号")
    affected_orders: list[AffectedOrderVO] = Field(..., description="受影响订单列表")
    estimated_delay_hours: float = Field(..., description="预计总延迟小时数")
    adjustment_plan: AdjustmentPlanVO = Field(..., description="调整方案")
