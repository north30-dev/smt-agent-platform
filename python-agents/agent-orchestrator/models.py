"""编排 Agent 的 Pydantic 请求/响应模型。

字段命名统一 snake_case，与 OpenAPI 契约对齐。
"""

from pydantic import BaseModel, Field


class DeviceFaultRequest(BaseModel):
    """设备故障编排请求体。"""

    device_id: int = Field(..., ge=1, description="设备 ID")
    symptom: str = Field(..., min_length=1, max_length=2000, description="故障现象描述")


class WorkflowResponse(BaseModel):
    """编排工作流响应。"""

    workflow_id: str = Field(..., description="工作流 ID")
    status: str = Field(
        ..., description="工作流状态：SUCCESS / PARTIAL / FAILED"
    )
    diagnosis: dict | None = Field(
        None, description="maintenance Agent 诊断结果"
    )
    quality_assessment: dict | None = Field(
        None, description="quality Agent 质量评估结果"
    )
    schedule_adjustment: dict | None = Field(
        None, description="scheduler Agent 急单调整结果"
    )
    summary: str | None = Field(None, description="LLM 汇总摘要")
    errors: dict[str, str] = Field(
        default_factory=dict, description="各节点错误信息"
    )
