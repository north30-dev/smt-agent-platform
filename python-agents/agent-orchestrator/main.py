"""agent-orchestrator FastAPI 应用。

端口 8005。对外提供设备故障编排入口与工作流查询接口。
路径前缀 /v1/orchestrator/**。

编排流程：设备故障 → 串行调用 maintenance → quality → scheduler → execution → LLM 汇总。
任何子 Agent 不可用时降级为 skipped 状态，工作流继续执行。

REL-1：工作流状态持久化到 PostgreSQL workflows 表（shared.db），进程重启不丢失。
"""

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from shared.config import settings
from shared.db import (
    close_pool,
    get_workflow as _get_workflow,
    init_workflow_table,
    save_workflow,
)
from shared.llm_client import LLMClientError
from shared.models import ErrorResponse
from shared.observability import (
    get_logger,
    register_health_endpoint,
    register_metrics_endpoint,
    setup_logging,
)

from .agent_clients import AgentUnavailable
from .graph import app_graph
from .models import DeviceFaultEventRequest, DeviceFaultRequest, WorkflowResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：startup 初始化 workflows 表，shutdown 关闭共享客户端（RES-1）。"""
    # startup：幂等创建 workflows 表
    try:
        await init_workflow_table()
    except Exception as exc:
        logger.warning("startup: init_workflow_table failed", error=str(exc))
    yield
    # shutdown：关闭共享 httpx 客户端与 PG 连接池
    try:
        from shared.llm_client import aclose as _aclose_llm

        await _aclose_llm()
    except Exception as exc:
        logger.warning("shutdown: close llm_client failed", error=str(exc))
    try:
        from .agent_clients import aclose as _aclose_agents

        await _aclose_agents()
    except Exception as exc:
        logger.warning("shutdown: close agent_clients failed", error=str(exc))
    try:
        await close_pool()
    except Exception as exc:
        logger.warning("shutdown: close pg pool failed", error=str(exc))


app = FastAPI(
    title="SMT Agent 编排服务",
    description=(
        "LangGraph 多智能体编排服务，串联运维诊断、质量根因分析、"
        "急单调度调整三阶段，并提供 LLM 汇总摘要。"
    ),
    version="0.3.0",
    lifespan=lifespan,
)

setup_logging(settings.log_level)
logger = get_logger("agent-orchestrator")
register_health_endpoint(app, "agent-orchestrator")
register_metrics_endpoint(app)


# 参与状态判定的节点列表（不含 execution/summary，二者不影响状态判定）
_STATUS_NODES = ["diagnosis", "quality_assessment", "schedule_adjustment"]


def _determine_status(result: dict) -> str:
    """根据结果判定工作流状态。

    - SUCCESS: 无 errors，且 _STATUS_NODES 中所有节点结果均存在且非 skipped
    - PARTIAL: 部分节点失败但至少一个成功
    - FAILED: 全部节点失败

    新增节点时只需更新 _STATUS_NODES 列表。
    """
    errors = result.get("errors") or {}

    node_results = []
    for key in _STATUS_NODES:
        value = result.get(key)
        ok = bool(value) and not (
            isinstance(value, dict) and value.get("status") == "skipped"
        )
        node_results.append(ok)

    success_count = sum(node_results)
    error_count = len(errors)

    if error_count == 0 and success_count == len(_STATUS_NODES):
        return "SUCCESS"
    if success_count == 0:
        return "FAILED"
    return "PARTIAL"


async def _run_device_fault_workflow(device_id: int, symptom: str) -> WorkflowResponse:
    """执行设备故障编排工作流（device_fault 与 device_fault_event 共享）。

    包含：生成 workflow_id → ainvoke → 状态判定 → 持久化 → 构造响应。
    """
    workflow_id = f"wf-{uuid4().hex[:12]}"
    initial_state = {
        "device_id": device_id,
        "symptom": symptom,
        "workflow_id": workflow_id,
        "diagnosis": None,
        "quality_assessment": None,
        "schedule_adjustment": None,
        "instructions": [],
        "summary": None,
        "errors": {},
    }

    result = await app_graph.ainvoke(initial_state)
    status = _determine_status(result)

    # REL-1：持久化工作流到 PostgreSQL，进程重启不丢失
    await save_workflow(workflow_id, status, result)
    logger.info(
        "orchestrator workflow completed",
        workflow_id=workflow_id,
        status=status,
        error_count=len(result.get("errors") or {}),
    )

    return WorkflowResponse(
        workflow_id=workflow_id,
        status=status,
        diagnosis=result.get("diagnosis"),
        quality_assessment=result.get("quality_assessment"),
        schedule_adjustment=result.get("schedule_adjustment"),
        instructions=result.get("instructions") or [],
        summary=result.get("summary"),
        errors=result.get("errors") or {},
    )


@app.post(
    "/v1/orchestrator/device_fault",
    response_model=WorkflowResponse,
)
async def device_fault(req: DeviceFaultRequest):
    """设备故障编排入口：串联 maintenance/quality/scheduler/execution → LLM 汇总。"""
    logger.info(
        "orchestrator device_fault invoked",
        device_id=req.device_id,
    )
    return await _run_device_fault_workflow(req.device_id, req.symptom)


@app.post(
    "/v1/orchestrator/device_fault_event",
    response_model=WorkflowResponse,
)
async def device_fault_event(req: DeviceFaultEventRequest):
    """事件驱动入口：接收 Kafka 消费者转发的设备异常事件，复用 device_fault 编排逻辑。"""
    logger.info(
        "orchestrator device_fault_event invoked",
        device_id=req.device_id,
        source=req.source,
    )
    return await _run_device_fault_workflow(req.device_id, req.symptom)


@app.get(
    "/v1/orchestrator/workflows/{workflow_id}",
    response_model=WorkflowResponse,
)
async def get_workflow(workflow_id: str):
    """查询已存储的工作流结果。"""
    stored = await _get_workflow(workflow_id)
    if stored is None:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="workflow_not_found",
                message=f"工作流不存在: {workflow_id}",
            ).model_dump(),
        )
    return WorkflowResponse(
        workflow_id=stored["workflow_id"],
        status=stored["status"],
        diagnosis=stored.get("diagnosis"),
        quality_assessment=stored.get("quality_assessment"),
        schedule_adjustment=stored.get("schedule_adjustment"),
        instructions=stored.get("instructions") or [],
        summary=stored.get("summary"),
        errors=stored.get("errors") or {},
    )


@app.exception_handler(AgentUnavailable)
async def agent_unavailable_handler(_request, exc: AgentUnavailable):
    """子 Agent 不可达 → 503（理论上 nodes 层已降级，此为兜底）。"""
    logger.warning("agent unavailable escaped nodes layer", error=str(exc))
    return JSONResponse(
        status_code=503,
        content=ErrorResponse(
            error="agent_unavailable", message=str(exc)
        ).model_dump(),
    )


@app.exception_handler(LLMClientError)
async def llm_error_handler(_request, exc: LLMClientError):
    """大模型不可达 → 503（summary 节点已降级，此为兜底）。"""
    logger.warning("llm unavailable", error=str(exc))
    return JSONResponse(
        status_code=503,
        content=ErrorResponse(
            error="llm_unavailable", message=str(exc)
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

    uvicorn.run(
        "agent-orchestrator.main:app",
        host="0.0.0.0",
        port=8005,
        reload=True,
    )
