"""质量分析 Agent 的 Pydantic 请求/响应模型。

字段命名统一 snake_case，与 OpenAPI 契约对齐。
"""

from pydantic import BaseModel, Field


class MonitorDatapoint(BaseModel):
    """单项缺陷监控数据点。"""

    datapoint_code: str = Field(..., description="采集点编码")
    value: float = Field(..., description="采集值")
    timestamp: str = Field(..., description="采集时间（ISO 字符串）")


class MonitorResponse(BaseModel):
    """实时缺陷监控响应。"""

    device_id: int = Field(..., description="设备 ID")
    defect_rate: float = Field(..., description="AOI 缺陷率均值")
    threshold: float = Field(..., description="缺陷率阈值")
    status: str = Field(
        ..., description="状态（OK/ALERT/INSUFFICIENT_DATA）"
    )
    datapoints: list[MonitorDatapoint] = Field(..., description="采样数据点列表")
    analyzed_at: str = Field(..., description="分析时间（ISO 字符串）")


class RootCauseRequest(BaseModel):
    """质量根因分析请求体。"""

    device_id: int = Field(..., ge=1, description="设备 ID")
    defect_description: str = Field(
        ..., min_length=1, max_length=2000, description="缺陷描述"
    )


class SimilarCase(BaseModel):
    """相似历史质量案例。"""

    case_id: str = Field(..., description="案例 ID")
    description: str = Field(..., description="缺陷描述")
    root_cause: str = Field(..., description="根因")
    corrective_action: str = Field(..., description="纠正措施")
    score: float = Field(..., description="相似度得分")


class RootCause(BaseModel):
    """单项根因（按"人/机/料/法/环"五要素分类）。"""

    category: str = Field(..., description="根因类别（人/机/料/法/环）")
    cause: str = Field(..., description="根因描述")


class RootCauseResponse(BaseModel):
    """质量根因分析响应。"""

    device_id: int = Field(..., description="设备 ID")
    root_causes: list[RootCause] = Field(..., description="根因列表")
    corrective_actions: list[str] = Field(..., description="纠正措施列表")
    similar_cases: list[SimilarCase] = Field(
        ..., description="相似历史案例列表"
    )


class CaseCreateRequest(BaseModel):
    """质量案例录入请求体。"""

    defect_type: str = Field(
        ..., min_length=1, max_length=100, description="缺陷类型"
    )
    description: str = Field(
        ..., min_length=1, max_length=2000, description="缺陷描述"
    )
    root_cause: str = Field(
        ..., min_length=1, max_length=1000, description="根因"
    )
    corrective_action: str = Field(
        ..., min_length=1, max_length=2000, description="纠正措施"
    )


class CaseCreateResponse(BaseModel):
    """质量案例录入响应。"""

    case_id: str = Field(..., description="生成的案例 ID")


class AlertRecord(BaseModel):
    """质量告警记录。"""

    id: int = Field(..., description="告警自增 ID")
    device_id: int = Field(..., description="设备 ID")
    defect_rate: float = Field(..., description="缺陷率")
    threshold: float = Field(..., description="阈值")
    status: str = Field(..., description="状态")
    datapoint_code: str | None = Field(None, description="采集点编码")
    alert_time: str = Field(..., description="告警时间（ISO 字符串）")


class AlertsPageResponse(BaseModel):
    """质量告警分页响应。"""

    records: list[AlertRecord] = Field(..., description="告警记录列表")
    total: int = Field(..., description="总条数")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
