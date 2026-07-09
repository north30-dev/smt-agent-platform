"""调度智能体 FastAPI 应用。

端口 8001。提供订单录入与查询、排产计划生成与查询、急单插单响应五个接口。
对外路径前缀 /v1/scheduler/**（经 smt-gateway StripPrefix=2 后落地本服务）。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

from shared.config import settings
from shared.llm_client import LLMClientError
from shared.models import ErrorResponse
from shared.observability import (
    get_logger,
    register_health_endpoint,
    setup_logging,
)
from shared.vector_store import VectorStoreError

from . import order_store, planner, urgent
from shared.device_client import DeviceServiceUnavailable
from .models import (
    OrderCreateRequest,
    OrderListResponse,
    OrderResponse,
    PlanGenerateRequest,
    PlanResponse,
    UrgentRequest,
    UrgentResponse,
)

# VAL-4：合法订单状态枚举（与 api-contracts/openapi/agent_api.yaml 对齐）
VALID_ORDER_STATUSES = {"PENDING", "PLANNED", "COMPLETED", "CANCELLED"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：shutdown 时关闭共享 httpx 客户端（RES-1）。"""
    yield
    try:
        from shared.llm_client import aclose as _aclose_llm

        await _aclose_llm()
    except Exception as exc:
        logger.warning("shutdown: close llm_client failed", error=str(exc))


app = FastAPI(
    title="SMT 调度智能体",
    description=(
        "订单录入、智能排产、急单插单响应服务。"
        "基于订单优先级 + 设备状态 + 物料齐套生成最优排产计划。"
    ),
    version="0.3.0",
    lifespan=lifespan,
)

setup_logging(settings.log_level)
logger = get_logger("agent-scheduler")
register_health_endpoint(app, "agent-scheduler")


@app.post("/v1/scheduler/orders", response_model=OrderResponse)
async def create_order(req: OrderCreateRequest):
    """录入订单到 production_orders 表，初始状态 PENDING。"""
    order_id = await order_store.save_order(
        order_no=req.order_no,
        product_model=req.product_model,
        quantity=req.quantity,
        priority=req.priority,
        delivery_date=req.delivery_date,
        material_ready=req.material_ready,
    )
    return OrderResponse(
        order_id=order_id,
        order_no=req.order_no,
        product_model=req.product_model,
        quantity=req.quantity,
        priority=req.priority,
        delivery_date=req.delivery_date,
        material_ready=req.material_ready,
        status="PENDING",
        created_at="",
    )


@app.get("/v1/scheduler/orders", response_model=OrderListResponse)
async def list_orders(
    status: str | None = Query(None, description="按状态过滤订单"),
):
    """查询订单列表，可按状态筛选。"""
    if status is not None and status not in VALID_ORDER_STATUSES:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error="invalid_param",
                message=(
                    f"非法 status 值: {status}，"
                    f"合法值为 {sorted(VALID_ORDER_STATUSES)}"
                ),
            ).model_dump(),
        )
    records = await order_store.list_orders(status=status)
    return OrderListResponse(
        records=[OrderResponse(**r) for r in records],
        total=len(records),
    )


@app.post("/v1/scheduler/plan/generate", response_model=PlanResponse)
async def generate_plan(req: PlanGenerateRequest):
    """生成排产计划并落库，更新已排产订单状态为 PLANNED。"""
    result = await planner.generate_plan()
    return PlanResponse(**result)


@app.get("/v1/scheduler/plan/current", response_model=PlanResponse)
async def get_current_plan():
    """查询当前 ACTIVE 排产计划。"""
    plan = await order_store.get_current_plan()
    if plan is None:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="plan_not_found",
                message="当前无 ACTIVE 排产计划",
            ).model_dump(),
        )
    return PlanResponse(**plan)


@app.post("/v1/scheduler/urgent", response_model=UrgentResponse)
async def handle_urgent(req: UrgentRequest):
    """急单插单：录入急单并评估对当前排产的影响。"""
    result = await urgent.handle_urgent(req)
    return UrgentResponse(**result)


# ---------------------------------------------------------------------------
# 异常处理器（对齐 agent-maintenance）
# ---------------------------------------------------------------------------


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
    """参数错误（如 delivery_date 格式）→ 400。"""
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

    uvicorn.run("agent-scheduler.main:app", host="0.0.0.0", port=8001, reload=True)
