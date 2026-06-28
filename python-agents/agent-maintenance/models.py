"""设备运维 Agent 的 Pydantic 请求/响应模型。

字段命名统一 snake_case，与 OpenAPI 契约对齐。
"""

from pydantic import BaseModel, Field


class DiagnoseRequest(BaseModel):
    """故障诊断请求体。"""

    device_id: int = Field(..., ge=1, description="设备 ID")
    symptom: str = Field(..., min_length=1, max_length=1000, description="故障现象描述")


class SimilarCase(BaseModel):
    """相似历史故障案例。"""

    case_id: str = Field(..., description="案例 ID")
    symptom: str = Field(..., description="故障现象")
    root_cause: str = Field(..., description="根因")
    solution: str = Field(..., description="解决方案")
    score: float = Field(..., description="相似度得分")


class DiagnoseResponse(BaseModel):
    """故障诊断响应。"""

    root_causes: list[str] = Field(..., description="可能的根因列表，按可能性排序")
    repair_suggestions: list[str] = Field(..., description="维修建议列表")
    similar_cases: list[SimilarCase] = Field(..., description="相似历史案例列表")


class HealthResponse(BaseModel):
    """设备健康评估响应。"""

    device_id: int = Field(..., description="设备 ID")
    health_score: int = Field(..., description="设备健康评分（0-100）")
    status: str = Field(..., description="设备运行状态")
    risk_level: str = Field(..., description="风险等级（LOW/MEDIUM/HIGH）")
    analysis: str = Field(..., description="健康评估分析说明")


class ThresholdAlert(BaseModel):
    """阈值告警项。"""

    datapoint_code: str = Field(..., description="采集点编码")
    current_value: float = Field(..., description="当前值（滑动均值）")
    threshold: float = Field(..., description="阈值")
    severity: str = Field(..., description="严重程度（HIGH/MEDIUM/LOW）")


class ForecastItem(BaseModel):
    """单项数据点预测。"""

    datapoint_code: str = Field(..., description="采集点编码")
    predicted_value: float = Field(..., description="预测值（外推到阈值时的估计值）")
    hours_to_threshold: float | None = Field(
        ..., description="预计到达阈值的小时数，None 表示无法估算"
    )


class PredictResponse(BaseModel):
    """预测性维护响应。"""

    trend: str = Field(..., description="整体趋势（上升/下降/平稳/数据不足）")
    threshold_alerts: list[ThresholdAlert] = Field(..., description="阈值告警列表")
    forecast: ForecastItem | None = Field(..., description="最紧急的预测项，无则 None")
    recommendation: str = Field(..., description="运维建议")
    data_sufficient: bool = Field(..., description="数据是否充足")


class CaseCreateRequest(BaseModel):
    """故障案例录入请求体。"""

    device_type: str = Field(..., min_length=1, max_length=100, description="设备类型")
    symptom: str = Field(..., min_length=1, max_length=1000, description="故障现象")
    root_cause: str = Field(..., min_length=1, max_length=1000, description="根因")
    solution: str = Field(..., min_length=1, max_length=2000, description="解决方案")


class CaseCreateResponse(BaseModel):
    """故障案例录入响应。"""

    case_id: str = Field(..., description="生成的案例 ID")


class ErrorResponse(BaseModel):
    """统一错误响应。"""

    error: str = Field(..., description="错误码")
    message: str = Field(..., description="错误描述")
