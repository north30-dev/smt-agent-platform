"""跨 Agent 共享的 Pydantic 模型（P0 M11 从两 Agent 各自定义抽取）。"""

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """统一错误响应。"""

    error: str = Field(..., description="错误码")
    message: str = Field(..., description="错误描述")
