"""执行协同 Agent 的 Pydantic 请求/响应模型。

字段命名统一 snake_case，与 OpenAPI 契约对齐。
遵循 agent-quality/models.py 风格（Pydantic v2）。
"""

from enum import Enum

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# 枚举（str, Enum：与 DB 字段存储的字符串值一致）
# ---------------------------------------------------------------------------


class InstructionType(str, Enum):
    """指令类型。"""

    REPAIR = "REPAIR"
    PRODUCTION_ADJUST = "PRODUCTION_ADJUST"
    PARAM_CHANGE = "PARAM_CHANGE"


class InstructionStatus(str, Enum):
    """指令状态机。"""

    PENDING = "PENDING"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class InstructionPriority(str, Enum):
    """指令优先级。"""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    CRITICAL = "CRITICAL"


class ExceptionStatus(str, Enum):
    """异常记录状态。"""

    OPEN = "OPEN"
    ANALYZED = "ANALYZED"
    HANDLED = "HANDLED"
    CLOSED = "CLOSED"


class ApprovalDecision(str, Enum):
    """审批决定。"""

    APPROVE = "APPROVE"
    REJECT = "REJECT"


# ---------------------------------------------------------------------------
# 请求模型
# ---------------------------------------------------------------------------


class InstructionCreateRequest(BaseModel):
    """创建执行指令请求体。

    支持两种模式：
    1. 自动生成：提供 source_workflow_id，配合 diagnosis / schedule_adjustment，
       由本服务派生 REPAIR / PRODUCTION_ADJUST 指令。
    2. 手动创建：提供 type + payload，生成单条指令。

    二者必须提供其一，否则校验失败。
    """

    source_workflow_id: str | None = Field(
        None, description="来源 orchestrator 工作流 ID（自动生成模式）"
    )
    diagnosis: dict | None = Field(
        None, description="maintenance Agent 诊断结果（派生 REPAIR 指令）"
    )
    schedule_adjustment: dict | None = Field(
        None, description="scheduler 急单调整结果（派生 PRODUCTION_ADJUST 指令）"
    )
    type: InstructionType | None = Field(
        None, description="指令类型（手动模式必填）"
    )
    payload: dict | None = Field(None, description="指令载荷（手动模式必填）")
    priority: InstructionPriority = Field(
        InstructionPriority.MEDIUM, description="优先级"
    )

    @model_validator(mode="after")
    def _check_mode(self) -> "InstructionCreateRequest":
        """校验：必须提供 source_workflow_id 或 (type + payload) 二者之一。"""
        if self.source_workflow_id is not None:
            return self
        if self.type is not None and self.payload is not None:
            return self
        raise ValueError(
            "必须提供 source_workflow_id（自动生成模式）或 type + payload（手动模式）"
        )


class ProgressRequest(BaseModel):
    """更新指令进度请求体。"""

    status: InstructionStatus = Field(..., description="目标状态")
    note: str | None = Field(None, description="备注")


class ApprovalRequest(BaseModel):
    """审批请求体。"""

    decision: ApprovalDecision = Field(..., description="审批决定 approve/reject")
    approver: str = Field("system", description="审批人")
    comment: str | None = Field(None, description="审批意见")


class ExceptionCreateRequest(BaseModel):
    """创建异常记录请求体。"""

    source: str = Field(..., min_length=1, max_length=64, description="异常来源")
    instruction_id: str | None = Field(None, description="关联指令 ID")
    description: str = Field(..., min_length=1, description="异常描述")


class VerifyRequest(BaseModel):
    """异常验证请求体。"""

    passed: bool = Field(..., description="是否验证通过")
    note: str | None = Field(None, description="备注")


# ---------------------------------------------------------------------------
# 响应模型
# ---------------------------------------------------------------------------


class InstructionResponse(BaseModel):
    """执行指令响应。"""

    instruction_id: str = Field(..., description="指令 ID")
    source_workflow_id: str | None = Field(None, description="来源工作流 ID")
    type: str = Field(..., description="指令类型")
    payload: dict = Field(..., description="指令载荷")
    status: str = Field(..., description="指令状态")
    priority: str = Field(..., description="优先级")
    auto_execute: bool = Field(..., description="是否自动执行")
    created_at: str = Field(..., description="创建时间（ISO 字符串）")
    updated_at: str = Field(..., description="更新时间（ISO 字符串）")


class InstructionCreateResponse(BaseModel):
    """创建执行指令响应。"""

    instructions: list[InstructionResponse] = Field(
        ..., description="创建的指令列表"
    )


class InstructionListResponse(BaseModel):
    """指令分页响应。"""

    records: list[InstructionResponse] = Field(..., description="指令记录列表")
    total: int = Field(..., description="总条数")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")


class ExceptionResponse(BaseModel):
    """异常记录响应。"""

    exception_id: str = Field(..., description="异常 ID")
    source: str = Field(..., description="来源")
    instruction_id: str | None = Field(None, description="关联指令 ID")
    description: str = Field(..., description="异常描述")
    status: str = Field(..., description="异常状态")
    analysis: dict | None = Field(None, description="LLM 分析结果")
    created_at: str = Field(..., description="创建时间（ISO 字符串）")
    updated_at: str = Field(..., description="更新时间（ISO 字符串）")


class ExceptionListResponse(BaseModel):
    """异常分页响应。"""

    records: list[ExceptionResponse] = Field(..., description="异常记录列表")
    total: int = Field(..., description="总条数")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")


class ApprovalResponse(BaseModel):
    """审批记录响应。"""

    id: int = Field(..., description="审批自增 ID")
    instruction_id: str = Field(..., description="关联指令 ID")
    decision: str = Field(..., description="审批决定")
    approver: str | None = Field(None, description="审批人")
    comment: str | None = Field(None, description="审批意见")
    created_at: str = Field(..., description="创建时间（ISO 字符串）")


class VerifyResponse(BaseModel):
    """异常验证响应。"""

    exception_id: str = Field(..., description="异常 ID")
    status: str = Field(..., description="验证后状态")
    note: str | None = Field(None, description="备注")
