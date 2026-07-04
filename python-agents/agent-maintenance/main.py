"""设备运维 Agent FastAPI 应用。

端口 8002。提供设备健康评估、故障诊断、预测性维护、故障案例录入四个接口。
对外路径前缀 /v1/maintenance/**（经 smt-gateway StripPrefix=2 后落地本服务）。
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from shared.config import settings
from shared.llm_client import LLMClientError
from shared.models import ErrorResponse
from shared.observability import get_logger, register_health_endpoint, setup_logging
from shared.vector_store import VectorStoreError

from . import diagnose, predict
from .device_client import DeviceServiceUnavailable, device_client
from .models import (
    CaseCreateRequest,
    CaseCreateResponse,
    DiagnoseRequest,
    DiagnoseResponse,
    HealthResponse,
    PredictResponse,
)

app = FastAPI(
    title="SMT 设备运维 Agent",
    description="设备故障诊断、健康评估与预测性维护服务。",
    version="0.2.0",
)

setup_logging(settings.log_level)
logger = get_logger("agent-maintenance")
register_health_endpoint(app, "agent-maintenance")


@app.get("/v1/maintenance/health/{device_id}", response_model=HealthResponse)
async def health(device_id: int):
    """设备健康评估：读取设备健康评分，计算风险等级。"""
    device = await device_client.get_device(device_id)
    raw_score = device.get("healthScore")
    try:
        health_score = int(raw_score)
    except (TypeError, ValueError):
        # 上游数据异常 → 503 而非 400（P0 M6）
        raise DeviceServiceUnavailable(
            f"device-service 返回的 healthScore 非法: {raw_score!r}"
        )
    status = str(device.get("status") or "UNKNOWN")

    if health_score >= 85:
        risk_level = "LOW"
        analysis = "设备健康状态良好，可继续正常运行"
    elif health_score >= 60:
        risk_level = "MEDIUM"
        analysis = "设备健康状态一般，建议关注并安排巡检"
    else:
        risk_level = "HIGH"
        analysis = "设备健康状态较差，建议立即检查"

    return HealthResponse(
        device_id=device_id,
        health_score=health_score,
        status=status,
        risk_level=risk_level,
        analysis=analysis,
    )


@app.post("/v1/maintenance/diagnose", response_model=DiagnoseResponse)
async def diagnose_fault(req: DiagnoseRequest):
    """故障诊断：基于设备信息与相似案例生成根因假设与维修建议。"""
    result = await diagnose.diagnose(req.device_id, req.symptom)
    return DiagnoseResponse(**result)


@app.get("/v1/maintenance/predict/{device_id}", response_model=PredictResponse)
async def predict_device(device_id: int):
    """预测性维护：基于近 7 天采集数据给出趋势与告警。"""
    result = await predict.predict(device_id)
    return PredictResponse(**result)


@app.post("/v1/maintenance/cases", response_model=CaseCreateResponse)
async def create_case(req: CaseCreateRequest):
    """录入故障案例到向量库，供后续诊断检索。"""
    case_id = await diagnose.create_case(
        device_type=req.device_type,
        symptom=req.symptom,
        root_cause=req.root_cause,
        solution=req.solution,
    )
    return CaseCreateResponse(case_id=case_id)


@app.exception_handler(DeviceServiceUnavailable)
async def device_service_unavailable_handler(_request, exc: DeviceServiceUnavailable):
    """device-service 不可达 → 503。"""
    logger.warning("device service unavailable", error=str(exc))
    return JSONResponse(
        status_code=503,
        content=ErrorResponse(
            error="device_service_unavailable", message=str(exc)
        ).model_dump(),
    )


@app.exception_handler(LLMClientError)
async def llm_error_handler(_request, exc: LLMClientError):
    """大模型不可达 → 503。"""
    logger.warning("llm unavailable", error=str(exc))
    return JSONResponse(
        status_code=503,
        content=ErrorResponse(
            error="llm_unavailable", message=str(exc)
        ).model_dump(),
    )


@app.exception_handler(VectorStoreError)
async def vector_store_error_handler(_request, exc: VectorStoreError):
    """向量库不可达 → 503。"""
    logger.warning("vector store unavailable", error=str(exc))
    return JSONResponse(
        status_code=503,
        content=ErrorResponse(
            error="vector_store_unavailable", message=str(exc)
        ).model_dump(),
    )


@app.exception_handler(ValueError)
async def value_error_handler(_request, exc: ValueError):
    """参数错误 → 400。"""
    logger.warning("invalid param", error=str(exc))
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error="invalid_param", message=str(exc)
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def internal_error_handler(_request, exc: Exception):
    """未知异常兜底 → 500。"""
    logger.exception("unhandled exception", error=str(exc))
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="internal_error", message="内部错误"
        ).model_dump(),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("agent-maintenance.main:app", host="0.0.0.0", port=8002, reload=True)
