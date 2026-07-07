"""LangGraph 节点函数。

每个节点接收 OrchestratorState，返回 partial state dict 合并到状态。
所有节点对 AgentUnavailable 做降级处理（写入 errors + skipped 状态），
绝不向上抛出，确保线性图能跑完所有节点。

节点顺序：maintenance → quality → scheduler → summary
"""

import json
import time
from datetime import date, timedelta

from shared import llm_client
from shared.llm_client import LLMClientError

from .agent_clients import AgentUnavailable, agent_clients
from .state import OrchestratorState


def _merge_errors(current: dict[str, str], key: str, message: str) -> dict[str, str]:
    """读取当前 errors，追加新错误 key 后返回完整 dict。

    线性图中每个节点读取的是上一节点写入的最新 state，因此连续失败时
    所有错误都会被顺序累积保留。
    """
    new_errors = dict(current or {})
    new_errors[key] = message
    return new_errors


async def maintenance_node(state: OrchestratorState) -> dict:
    """调用 maintenance diagnose。

    成功 → 写入 diagnosis。
    失败 → diagnosis=None，errors 记录 maintenance 错误。
    """
    try:
        result = await agent_clients.call_maintenance(
            state["device_id"], state["symptom"]
        )
    except AgentUnavailable as exc:
        return {
            "diagnosis": None,
            "errors": _merge_errors(state.get("errors", {}), "maintenance", str(exc)),
        }
    return {"diagnosis": result}


async def quality_node(state: OrchestratorState) -> dict:
    """调用 quality root_cause。

    成功 → 写入 quality_assessment。
    失败 → quality_assessment={"status": "skipped", "reason": ...}，errors 记录。
    """
    try:
        result = await agent_clients.call_quality(
            state["device_id"], state["symptom"]
        )
    except AgentUnavailable as exc:
        return {
            "quality_assessment": {"status": "skipped", "reason": str(exc)},
            "errors": _merge_errors(state.get("errors", {}), "quality", str(exc)),
        }
    return {"quality_assessment": result}


async def scheduler_node(state: OrchestratorState) -> dict:
    """调用 scheduler urgent，构造合成急单。

    成功 → 写入 schedule_adjustment。
    失败 → schedule_adjustment={"status": "skipped", "reason": ...}，errors 记录。
    """
    # 合成急单：基于设备故障生成
    order_no = f"URGENT-FAULT-{state['device_id']}-{int(time.time())}"
    product_model = "UNKNOWN"
    quantity = 1000
    delivery_date = (date.today() + timedelta(days=2)).isoformat()

    try:
        result = await agent_clients.call_scheduler(
            order_no, product_model, quantity, delivery_date
        )
    except AgentUnavailable as exc:
        return {
            "schedule_adjustment": {"status": "skipped", "reason": str(exc)},
            "errors": _merge_errors(state.get("errors", {}), "scheduler", str(exc)),
        }
    return {"schedule_adjustment": result}


async def summary_node(state: OrchestratorState) -> dict:
    """基于前三个节点结果，调用 LLM 生成 ≤300 字汇总摘要。

    失败 → 返回固定降级摘要，不写入 errors（摘要失败不影响主流程状态判定）。
    """
    prompt = _build_summary_prompt(state)
    try:
        summary_text = await llm_client.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "你是 SMT 产线运维助手。基于设备故障的运维诊断、"
                        "质量根因分析、急单调度调整三方面结果，"
                        "生成不超过 300 字的中文汇总摘要，"
                        "包含关键风险、根因假设、调度影响与建议动作。"
                    ),
                },
                {"role": "user", "content": prompt},
            ]
        )
    except LLMClientError:
        return {"summary": "摘要生成失败，详见各节点结果。"}
    return {"summary": summary_text}


def _build_summary_prompt(state: OrchestratorState) -> str:
    """根据三个节点结果构造 LLM 输入 prompt。"""
    parts = [
        f"设备 ID: {state['device_id']}",
        f"故障现象: {state['symptom']}",
    ]

    diagnosis = state.get("diagnosis")
    if diagnosis:
        parts.append(
            "运维诊断: " + _safe_json(diagnosis, max_chars=800)
        )
    else:
        parts.append("运维诊断: （未生成，maintenance Agent 不可用）")

    quality = state.get("quality_assessment")
    if quality and quality.get("status") != "skipped":
        parts.append(
            "质量根因分析: " + _safe_json(quality, max_chars=800)
        )
    elif quality and quality.get("status") == "skipped":
        parts.append(f"质量根因分析: （已跳过：{quality.get('reason', '未知')}）")
    else:
        parts.append("质量根因分析: （未生成）")

    schedule = state.get("schedule_adjustment")
    if schedule and schedule.get("status") != "skipped":
        parts.append(
            "急单调度调整: " + _safe_json(schedule, max_chars=800)
        )
    elif schedule and schedule.get("status") == "skipped":
        parts.append(f"急单调度调整: （已跳过：{schedule.get('reason', '未知')}）")
    else:
        parts.append("急单调度调整: （未生成）")

    errors = state.get("errors") or {}
    if errors:
        parts.append("降级节点: " + ", ".join(f"{k}={v}" for k, v in errors.items()))

    return "\n".join(parts)


def _safe_json(obj, max_chars: int = 800) -> str:
    """安全 JSON 序列化，超长截断。"""
    try:
        text = json.dumps(obj, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        text = str(obj)
    if len(text) > max_chars:
        text = text[:max_chars] + "...(截断)"
    return text
