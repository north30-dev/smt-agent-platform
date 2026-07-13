"""执行协同 Agent FastAPI 应用。

端口 8006。提供执行指令管理、审批、进度更新、异常记录与验证接口。
对外路径前缀 /v1/execution/**（经 smt-gateway StripPrefix=2 后落地本服务）。

闭环职责：
1. 将 orchestrator 决策（diagnosis / schedule_adjustment）转为可执行指令；
2. 管理指令状态机（PENDING → APPROVED → EXECUTING → COMPLETED/FAILED）；
3. 处理人工审批（PENDING_APPROVAL → APPROVED/REJECTED）；
4. 消费 Kafka device.anomaly 事件，自动触发 orchestrator 编排并落指令；
5. 记录与分析执行异常。

遵循 agent-quality/main.py / agent-orchestrator/main.py 结构：
lifespan 管理 DB 表初始化 + Kafka 消费者 + 共享客户端关闭。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

from shared.config import settings
from shared.db import close_pool, init_execution_tables
from shared.llm_client import LLMClientError
from shared.models import ErrorResponse
from shared.observability import get_logger, register_health_endpoint, register_metrics_endpoint, setup_logging

from . import exception_service, instruction_service, approval_service, kafka_consumer
from .models import (
    ApprovalRequest,
    ExceptionCreateRequest,
    ExceptionListResponse,
    ExceptionResponse,
    InstructionCreateRequest,
    InstructionCreateResponse,
    InstructionListResponse,
    InstructionResponse,
    ProgressRequest,
    VerifyRequest,
    VerifyResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期。

    startup：幂等创建 execution 三张表 + 启动 Kafka 消费者（best-effort）。
    shutdown：关闭 Kafka 消费者、共享 LLM httpx 客户端、PG 连接池。
    所有阶段异常均降级为日志，不阻塞启动/关闭。
    """
    try:
        await init_execution_tables()
    except Exception as exc:
        logger.warning("startup: init_execution_tables failed", error=str(exc))
    try:
        await kafka_consumer.start()
    except Exception as exc:
        logger.warning("startup: kafka consumer failed", error=str(exc))
    yield
    try:
        await kafka_consumer.aclose()
    except Exception as exc:
        logger.warning("shutdown: kafka consumer close failed", error=str(exc))
    try:
        from shared.llm_client import aclose as _aclose_llm

        await _aclose_llm()
    except Exception as exc:
        logger.warning("shutdown: close llm_client failed", error=str(exc))
    try:
        await close_pool()
    except Exception as exc:
        logger.warning("shutdown: close pg pool failed", error=str(exc))


app = FastAPI(
    title="SMT 执行协同 Agent",
    description=(
        "SMT 产线执行协同服务：将 orchestrator 决策转为可执行指令，"
        "管理指令状态机、人工审批、异常记录，并消费 Kafka 设备异常事件。"
    ),
    version="0.4.0",
    lifespan=lifespan,
)

setup_logging(settings.log_level)
logger = get_logger("agent-execution")
register_health_endpoint(app, "agent-execution")
register_metrics_endpoint(app)


# ---------------------------------------------------------------------------
# 指令接口
# ---------------------------------------------------------------------------


@app.post(
    "/v1/execution/instructions", response_model=InstructionCreateResponse
)
async def create_instructions(req: InstructionCreateRequest):
    """创建执行指令（自动生成 / 手动）。"""
    records = await instruction_service.create_instructions(req)
    return InstructionCreateResponse(
        instructions=[InstructionResponse(**r) for r in records]
    )


@app.get(
    "/v1/execution/instructions", response_model=InstructionListResponse
)
async def list_instructions(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    size: int = Query(20, ge=1, le=200, description="每页条数，1-200"),
    status: str | None = Query(None, description="状态过滤"),
    instruction_type: str | None = Query(None, description="类型过滤"),
):
    """分页查询执行指令。"""
    result = await instruction_service.list_instructions(
        page, size, status, instruction_type
    )
    return InstructionListResponse(
        records=[InstructionResponse(**r) for r in result["records"]],
        total=result["total"],
        page=result["page"],
        size=result["size"],
    )


@app.get(
    "/v1/execution/instructions/{instruction_id}",
    response_model=InstructionResponse,
)
async def get_instruction(instruction_id: str):
    """查询单条指令，不存在返回 404。"""
    result = await instruction_service.get_instruction(instruction_id)
    if result is None:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="INSTRUCTION_NOT_FOUND",
                message=f"指令不存在: {instruction_id}",
            ).model_dump(),
        )
    return InstructionResponse(**result)


@app.post(
    "/v1/execution/instructions/{instruction_id}/approve",
    response_model=InstructionResponse,
)
async def approve_instruction(instruction_id: str, req: ApprovalRequest):
    """审批指令（approve / reject）。"""
    result = await approval_service.approve(instruction_id, req)
    return InstructionResponse(**result)


@app.post(
    "/v1/execution/instructions/{instruction_id}/progress",
    response_model=InstructionResponse,
)
async def update_progress(instruction_id: str, req: ProgressRequest):
    """更新指令进度（状态机校验）。"""
    result = await instruction_service.update_progress(instruction_id, req)
    return InstructionResponse(**result)


# ---------------------------------------------------------------------------
# 异常接口
# ---------------------------------------------------------------------------


@app.post("/v1/execution/exceptions", response_model=ExceptionResponse)
async def create_exception(req: ExceptionCreateRequest):
    """创建异常记录。"""
    result = await exception_service.create_exception(req)
    return ExceptionResponse(**result)


@app.get(
    "/v1/execution/exceptions", response_model=ExceptionListResponse
)
async def list_exceptions(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    size: int = Query(20, ge=1, le=200, description="每页条数，1-200"),
    status: str | None = Query(None, description="状态过滤"),
):
    """分页查询异常记录。"""
    result = await exception_service.list_exceptions(page, size, status)
    return ExceptionListResponse(
        records=[ExceptionResponse(**r) for r in result["records"]],
        total=result["total"],
        page=result["page"],
        size=result["size"],
    )


@app.post(
    "/v1/execution/exceptions/{exception_id}/verify",
    response_model=VerifyResponse,
)
async def verify_exception(exception_id: str, req: VerifyRequest):
    """验证异常（通过 → CLOSED；未通过 → OPEN）。"""
    result = await exception_service.verify_exception(exception_id, req)
    return VerifyResponse(
        exception_id=result["exception_id"],
        status=result["status"],
        note=req.note,
    )


@app.post(
    "/v1/execution/exceptions/{exception_id}/analyze",
    response_model=ExceptionResponse,
)
async def analyze_exception(exception_id: str):
    """对异常进行 LLM 根因分析，状态推进为 ANALYZED。"""
    result = await exception_service.analyze_exception(exception_id)
    return ExceptionResponse(**result)


@app.post(
    "/v1/execution/exceptions/{exception_id}/handle",
    response_model=ExceptionResponse,
)
async def handle_exception(exception_id: str):
    """推进异常状态 ANALYZED → HANDLED。"""
    result = await exception_service.handle_exception(exception_id)
    return ExceptionResponse(**result)


# ---------------------------------------------------------------------------
# 异常处理兜底
# ---------------------------------------------------------------------------


@app.exception_handler(LLMClientError)
async def llm_error_handler(_request, exc: LLMClientError):
    """大模型不可达 → 503。"""
    logger.warning("llm unavailable", error=str(exc))
    return JSONResponse(
        status_code=503,
        content=ErrorResponse(
            error="LLM_UNAVAILABLE", message=str(exc)
        ).model_dump(),
    )


@app.exception_handler(ValueError)
async def value_error_handler(_request, exc: ValueError):
    """参数错误 / 非法状态跳转 / 资源不存在校验 → 400。"""
    logger.warning("invalid param", error=str(exc))
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error="INVALID_PARAM", message=str(exc)
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def internal_error_handler(_request, exc: Exception):
    """未知异常兜底 → 500。"""
    logger.exception("unhandled exception", error=str(exc))
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="UNEXPECTED_ERROR", message="内部错误"
        ).model_dump(),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "agent-execution.main:app", host="0.0.0.0", port=8006, reload=True
    )
