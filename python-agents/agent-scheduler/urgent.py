"""急单插单响应模块。

流程：
1. 录入急单到 production_orders（priority=URGENT，物料默认齐套）
2. 比对当前 ACTIVE 排产计划，找出受影响订单
3. 调 LLM 生成调整方案（换线建议 / 加班建议）
4. 返回 {affected_orders, estimated_delay_hours, adjustment_plan}

错误不在本模块捕获，统一交由 main.py 异常处理器兜底。
"""

import json
import math
from functools import lru_cache
from pathlib import Path

import yaml

from shared import llm_client
from shared.config import settings
from shared.text_utils import extract_json_block as _extract_json_block, truncate as _truncate

from . import order_store

# Prompt 模板文件
_PROMPT_FILE = Path(__file__).parent.parent / "shared" / "prompts" / "system_prompt.yaml"


async def handle_urgent(req) -> dict:
    """处理急单插单请求。

    Args:
        req: UrgentRequest 实例（含 order_no/product_model/quantity/delivery_date/source）。

    Returns:
        匹配 UrgentResponse 字段的 dict。
    """
    # 1. 录入急单（priority=URGENT，物料默认齐套）
    # 急单单号落库后由后续 list_orders/generate_plan 流程消费，此处不直接返回
    await order_store.save_order(
        order_no=req.order_no,
        product_model=req.product_model,
        quantity=req.quantity,
        priority="URGENT",
        delivery_date=req.delivery_date,
        material_ready=True,
        source=req.source,
    )

    # 2. 比对当前 ACTIVE 计划
    current_plan = await order_store.get_current_plan()
    if not current_plan:
        return {
            "urgent_order_no": req.order_no,
            "affected_orders": [],
            "estimated_delay_hours": 0.0,
            "adjustment_plan": {
                "changeover_suggestion": "当前无排产计划，可直接排入",
                "overtime_suggestion": "无需加班",
            },
        }

    # 3. 计算急单占用时长与受影响订单
    urgent_duration = _estimate_duration(req.quantity)
    affected_orders = _find_affected_orders(
        current_plan.get("allocations") or [], urgent_duration
    )
    estimated_delay_hours = round(
        sum(a["delay_hours"] for a in affected_orders), 2
    )

    # 4. 调 LLM 生成调整方案
    # 注意：模板内含 JSON 示例 {"changeover_suggestion": ...}，与 str.format()
    # 占位语法冲突，改用 str.replace() 逐个替换占位符。
    system_prompt, urgent_template = _load_prompts()
    user_content = urgent_template
    user_content = user_content.replace(
        "{urgent_order}",
        _truncate(
            json.dumps(
                {
                    "order_no": req.order_no,
                    "product_model": req.product_model,
                    "quantity": req.quantity,
                    "delivery_date": req.delivery_date,
                    "duration_hours": urgent_duration,
                },
                ensure_ascii=False,
            ),
            800,
        ),
    )
    user_content = user_content.replace(
        "{current_plan}",
        _truncate(
            json.dumps(current_plan, ensure_ascii=False, default=str),
            1500,
        ),
    )
    user_content = user_content.replace(
        "{affected_orders}",
        _truncate(
            json.dumps(affected_orders, ensure_ascii=False), 1200
        ),
    )
    user_content = user_content.replace(
        "{delay_hours}", str(estimated_delay_hours)
    )

    raw = await llm_client.chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
    )
    adjustment_plan = _parse_adjustment_plan(raw)

    return {
        "urgent_order_no": req.order_no,
        "affected_orders": affected_orders,
        "estimated_delay_hours": estimated_delay_hours,
        "adjustment_plan": adjustment_plan,
    }


def _estimate_duration(quantity: int) -> float:
    """根据订单数量估算占用时长（小时）。

    duration = ceil(quantity / capacity_per_hour) + changeover_minutes/60
    """
    capacity = max(settings.scheduler_capacity_per_hour, 1)
    production = max(1.0, math.ceil(quantity / capacity))
    changeover = settings.scheduler_changeover_minutes / 60.0
    return float(production + changeover)


def _find_affected_orders(
    allocations: list[dict], urgent_duration: float
) -> list[dict]:
    """识别受急单影响的订单。

    简化启发式：对每条 allocation，若其所在设备被急单占用（start_hour <
    urgent_duration 视为时间窗冲突），则视为受影响，延迟时长 = urgent_duration。

    Args:
        allocations: 当前计划中的分配项列表。
        urgent_duration: 急单预计占用时长。

    Returns:
        受影响订单列表，每项含 order_no/product_model/delay_hours。
    """
    affected: list[dict] = []
    for alloc in allocations:
        try:
            start_hour = float(alloc.get("start_hour") or 0)
        except (TypeError, ValueError):
            start_hour = 0.0
        if start_hour < urgent_duration:
            affected.append(
                {
                    "order_no": str(alloc.get("order_no") or ""),
                    "product_model": str(alloc.get("product_model") or ""),
                    "delay_hours": float(urgent_duration),
                }
            )
    return affected


@lru_cache(maxsize=1)
def _load_prompts() -> tuple[str, str]:
    """读取 system_prompt.yaml 中的 scheduler.system 与 urgent_template。"""
    with _PROMPT_FILE.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    scheduler = data["scheduler"]
    return scheduler["system"], scheduler["urgent_template"]


def _parse_adjustment_plan(raw_text: str) -> dict:
    """解析 LLM 输出为 {changeover_suggestion, overtime_suggestion}。

    期望 LLM 输出 JSON：{"changeover_suggestion": "...", "overtime_suggestion": "..."}
    解析失败时降级为占位提示（不抛异常，保证响应可用）。
    """
    text = (raw_text or "").strip()
    # 1. 尝试直接解析
    try:
        data = json.loads(text)
        return _build_adjustment(data)
    except (ValueError, TypeError):
        pass

    # 2. 尝试从代码块提取
    code = _extract_json_block(text)
    if code is not None:
        try:
            data = json.loads(code)
            return _build_adjustment(data)
        except (ValueError, TypeError):
            pass

    # 3. 降级：把原始文本作为换线建议
    return {
        "changeover_suggestion": _truncate(text, 200) or "（LLM 输出解析失败）",
        "overtime_suggestion": "（LLM 输出解析失败，请人工评估）",
    }


def _build_adjustment(data) -> dict:
    """从 dict 中提取两个字段，缺失补默认。"""
    if not isinstance(data, dict):
        return {
            "changeover_suggestion": "（LLM 输出格式异常）",
            "overtime_suggestion": "（LLM 输出格式异常）",
        }
    changeover = str(data.get("changeover_suggestion") or "").strip()
    overtime = str(data.get("overtime_suggestion") or "").strip()
    return {
        "changeover_suggestion": changeover or "（LLM 未给出换线建议）",
        "overtime_suggestion": overtime or "（LLM 未给出加班建议）",
    }
