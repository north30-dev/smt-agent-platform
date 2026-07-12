"""异常记录业务逻辑。

封装异常创建、列表、LLM 根因分析、验证的业务规则。
DB CRUD 委托 shared.db（create_exception / get_exception / list_exceptions /
update_exception_status）；LLM 调用委托 shared.llm_client。

错误不在本模块捕获，统一交由 main.py 异常处理器兜底。
LLM 不可用时降级为带 status=degraded 的分析结果，不向上抛。
"""

import json

from shared import db, llm_client
from shared.llm_client import LLMClientError

from .models import ExceptionCreateRequest, VerifyRequest


async def create_exception(req: ExceptionCreateRequest) -> dict:
    """创建异常记录，exception_id = f"exc-{uuid4().hex[:12]}"。"""
    from uuid import uuid4

    exception_id = f"exc-{uuid4().hex[:12]}"
    return await db.create_exception(
        exception_id=exception_id,
        source=req.source,
        instruction_id=req.instruction_id,
        description=req.description,
    )


async def list_exceptions(
    page: int = 1, size: int = 20, status: str | None = None
) -> dict:
    """分页查询异常记录。"""
    return await db.list_exceptions(page, size, status)


async def analyze_exception(exception_id: str) -> dict:
    """对异常进行 LLM 根因分析，更新状态为 ANALYZED。

    LLM 不可用（LLMClientError）时降级为带 status=degraded 的分析结果，
    仍将状态推进到 ANALYZED，保证流程不阻塞。

    Raises:
        ValueError: 异常不存在。
    """
    exc = await db.get_exception(exception_id)
    if exc is None:
        raise ValueError(f"异常不存在: {exception_id}")

    messages = [
        {
            "role": "system",
            "content": (
                "你是 SMT 产线异常根因分析专家。请以纯 JSON 格式输出分析结果，"
                "包含 root_cause（根因）和 action（处理建议）两个字段，"
                "不要输出 JSON 以外的内容。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"异常来源: {exc['source']}\n"
                f"关联指令: {exc.get('instruction_id')}\n"
                f"描述: {exc['description']}\n"
                f"请分析根因并给出处理建议。"
            ),
        },
    ]

    try:
        response = await llm_client.chat(messages)
    except LLMClientError as exc_err:
        analysis = {
            "status": "degraded",
            "message": f"LLM 不可用，降级分析: {exc_err}",
        }
    else:
        try:
            analysis = json.loads(response)
        except (ValueError, TypeError):
            # LLM 未返回纯 JSON，包装为 manual_review
            analysis = {
                "root_cause": response,
                "action": "manual_review",
            }

    result = await db.update_exception_status(
        exception_id, "ANALYZED", analysis=analysis
    )
    if result is None:
        raise ValueError(f"异常不存在: {exception_id}")
    return result


async def verify_exception(exception_id: str, req: VerifyRequest) -> dict:
    """验证异常：通过 → CLOSED；未通过 → 回退 OPEN。

    Raises:
        ValueError: 异常不存在。
    """
    exc = await db.get_exception(exception_id)
    if exc is None:
        raise ValueError(f"异常不存在: {exception_id}")
    new_status = "CLOSED" if req.passed else "OPEN"
    result = await db.update_exception_status(exception_id, new_status)
    if result is None:
        raise ValueError(f"异常不存在: {exception_id}")
    return result


async def handle_exception(exception_id: str) -> dict:
    """推进异常状态 ANALYZED → HANDLED。

    Raises:
        ValueError: 异常不存在或不在 ANALYZED 状态。
    """
    exc = await db.get_exception(exception_id)
    if exc is None:
        raise ValueError(f"异常不存在: {exception_id}")
    if exc["status"] != "ANALYZED":
        raise ValueError(f"异常不在 ANALYZED 状态: {exc['status']}")
    result = await db.update_exception_status(exception_id, "HANDLED")
    if result is None:
        raise ValueError(f"异常不存在: {exception_id}")
    return result
