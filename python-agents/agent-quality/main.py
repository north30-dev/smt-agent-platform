"""质量分析 Agent FastAPI 应用。

端口 8003。提供实时缺陷监控、根因分析、案例录入、告警查询四个接口。
对外路径前缀 /v1/quality/**（经 smt-gateway StripPrefix=2 后落地本服务）。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

from shared.config import settings
from shared.llm_client import LLMClientError
from shared.models import ErrorResponse
from shared.observability import get_logger, register_health_endpoint, setup_logging
from shared.vector_store import VectorStoreError

# agent-quality 本地的 device-service 异常类型
from shared.device_client import DeviceServiceUnavailable

from . import alert_store, monitor, root_cause
from .models import (
    AlertsPageResponse,
    CaseCreateRequest,
    CaseCreateResponse,
    MonitorResponse,
    RootCauseRequest,
    RootCauseResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：shutdown 时关闭共享 httpx 客户端（RES-1）。"""
    yield
    try:
        from shared.llm_client import aclose as _aclose_llm

        await _aclose_llm()
    except Exception as exc:
        logger.warning("shutdown: close llm_client failed", error=str(exc))
    try:
        from shared.device_client import aclose as _aclose_device

        await _aclose_device()
    except Exception as exc:
        logger.warning("shutdown: close device_client failed", error=str(exc))


app = FastAPI(
    title="SMT 质量分析 Agent",
    description="SMT 产线质量监控与根因分析服务。",
    version="0.3.0",
    lifespan=lifespan,
)

setup_logging(settings.log_level)
logger = get_logger("agent-quality")
register_health_endpoint(app, "agent-quality")


@app.get("/v1/quality/monitor/{device_id}", response_model=MonitorResponse)
async def monitor_defects(device_id: int):
    """实时缺陷监控：聚合 AOI 缺陷率并按阈值判定状态。"""
    result = await monitor.monitor(device_id)
    return MonitorResponse(**result)


@app.post("/v1/quality/root_cause", response_model=RootCauseResponse)
async def analyze_root_cause(req: RootCauseRequest):
    """质量根因分析：基于"人/机/料/法/环"五要素生成根因与纠正措施。"""
    result = await root_cause.analyze(req.device_id, req.defect_description)
    return RootCauseResponse(**result)


@app.post("/v1/quality/cases", response_model=CaseCreateResponse)
async def create_case(req: CaseCreateRequest):
    """录入质量案例到向量库，供后续根因分析检索。"""
    case_id = await root_cause.create_case(
        defect_type=req.defect_type,
        description=req.description,
        root_cause=req.root_cause,
        corrective_action=req.corrective_action,
    )
    return CaseCreateResponse(case_id=case_id)


@app.get("/v1/quality/alerts", response_model=AlertsPageResponse)
async def list_alerts(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    size: int | None = Query(None, ge=1, le=200, description="每页条数，1-200"),
):
    """分页查询质量告警记录。"""
    result = await alert_store.list_alerts(page, size)
    return AlertsPageResponse(**result)


@app.exception_handler(DeviceServiceUnavailable)
async def device_service_unavailable_handler(
    _request, exc: DeviceServiceUnavailable
):
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

    uvicorn.run("agent-quality.main:app", host="0.0.0.0", port=8003, reload=True)
