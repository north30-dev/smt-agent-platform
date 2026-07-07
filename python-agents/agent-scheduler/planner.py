"""排产计划生成模块。

基于订单优先级 + 交付日期 + 物料齐套 + 设备状态（device-service），
按简单规则生成"产品-机台-时段"分配，再由 LLM 生成自然语言说明。
错误不在本模块捕获，统一交由 main.py 异常处理器兜底。

排产规则：
1. 仅处理 status=PENDING 且 material_ready=True 的订单
2. 仅分配 status=RUNNING 且 healthScore ≥ 阈值的设备
3. 排序：URGENT 优先 → delivery_date 升序 → quantity 降序
4. 分配：按可用设备数轮询分配，每条订单 duration = ceil(quantity/capacity)
   + changeover_minutes/60，start_hour 为该设备累计偏移
"""

import json
import math
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import yaml

from shared import llm_client
from shared.config import settings

from . import order_store
from .device_client import device_client

# Prompt 模板文件
_PROMPT_FILE = Path(__file__).parent.parent / "shared" / "prompts" / "system_prompt.yaml"

# 优先级排序权重：URGENT=0、HIGH=1、NORMAL=2、LOW=3
_PRIORITY_ORDER = {"URGENT": 0, "HIGH": 1, "NORMAL": 2, "LOW": 3}


async def generate_plan() -> dict:
    """生成排产计划。

    Returns:
        匹配 PlanResponse 字段的 dict（status 为 ACTIVE 或 EMPTY）。
    """
    now_iso = _now_iso()

    # 1. 拉取 PENDING 订单
    orders = await order_store.list_orders(status="PENDING")
    # 2. 过滤物料未齐套订单
    ready_orders = [o for o in orders if o.get("material_ready")]
    if not ready_orders:
        return _empty_plan(
            "无可用订单（无 PENDING 且物料齐套的订单）", now_iso
        )

    # 3. 拉取 RUNNING 设备并按健康阈值过滤
    try:
        devices = await device_client.list_devices(status="RUNNING")
    except Exception:
        # device-service 不可达时交由 main 异常处理器兜底
        raise

    usable_devices = [
        d
        for d in devices
        if int(d.get("healthScore") or 0)
        >= settings.scheduler_device_min_health_score
    ]
    if not usable_devices:
        return _empty_plan(
            "无可用设备（无 status=RUNNING 且 healthScore 达阈值的设备）",
            now_iso,
        )

    # 4. 排序：URGENT 优先 → delivery_date 升序 → quantity 降序
    sorted_orders = sorted(
        ready_orders,
        key=lambda o: (
            _PRIORITY_ORDER.get(str(o.get("priority", "NORMAL")).upper(), 99),
            str(o.get("delivery_date") or ""),
            -int(o.get("quantity") or 0),
        ),
    )

    # 5. 轮询分配
    allocations = _round_robin_allocate(sorted_orders, usable_devices)

    # 6. 加载 prompt，调 LLM 生成说明
    system_prompt, plan_template = _load_prompts()
    user_content = plan_template.format(
        orders=_truncate(json.dumps(sorted_orders, ensure_ascii=False), 1500),
        devices=_truncate(
            json.dumps(
                [
                    {
                        "id": d.get("id"),
                        "deviceName": d.get("deviceName"),
                        "deviceType": d.get("deviceType"),
                        "productionLine": d.get("productionLine"),
                        "healthScore": d.get("healthScore"),
                    }
                    for d in usable_devices
                ],
                ensure_ascii=False,
            ),
            800,
        ),
        allocations=_truncate(
            json.dumps(allocations, ensure_ascii=False), 1500
        ),
    )

    description = await llm_client.chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
    )
    description = _truncate(description.strip(), 200)

    # 7. 落库
    plan_version = await order_store.get_next_plan_version()
    plan_id = await order_store.save_plan(allocations, description, plan_version)

    # 8. 更新已排产订单状态为 PLANNED
    allocated_order_ids = {a.get("order_id") for a in allocations}
    for order in sorted_orders:
        if order.get("order_id") in allocated_order_ids:
            await order_store.update_order_status(
                int(order["order_id"]), "PLANNED"
            )

    return {
        "plan_id": plan_id,
        "plan_version": plan_version,
        "allocations": allocations,
        "description": description,
        "status": "ACTIVE",
        "created_at": now_iso,
    }


def _round_robin_allocate(
    orders: list[dict], devices: list[dict]
) -> list[dict]:
    """轮询分配订单到设备，返回 allocations 列表。

    每台设备维护一个累计 start_hour，按订单顺序轮询分配到各设备。
    """
    allocations: list[dict] = []
    device_cursors = [
        {"device": d, "start_hour": 0} for d in devices
    ]
    capacity_per_hour = settings.scheduler_capacity_per_hour
    changeover_hours = settings.scheduler_changeover_minutes / 60.0

    for idx, order in enumerate(orders):
        slot = device_cursors[idx % len(device_cursors)]
        device = slot["device"]
        quantity = int(order.get("quantity") or 0)
        # 至少 1 小时，避免 quantity 极小导致 duration=0
        production_hours = max(
            1.0, math.ceil(quantity / max(capacity_per_hour, 1))
        )
        duration = production_hours + changeover_hours
        start_hour = slot["start_hour"]

        allocations.append(
            {
                "order_id": int(order["order_id"]),
                "order_no": str(order["order_no"]),
                "product_model": str(order["product_model"]),
                "device_id": int(device.get("id") or 0),
                "device_name": str(device.get("deviceName") or ""),
                "start_hour": int(start_hour),
                "duration_hours": float(duration),
            }
        )
        slot["start_hour"] = start_hour + int(math.ceil(duration))

    return allocations


@lru_cache(maxsize=1)
def _load_prompts() -> tuple[str, str]:
    """读取 system_prompt.yaml 中的 scheduler.system 与 plan_template。

    Prompt 文件运行期不变，用 lru_cache 避免每次请求重复读盘。
    """
    with _PROMPT_FILE.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    scheduler = data["scheduler"]
    return scheduler["system"], scheduler["plan_template"]


def _empty_plan(description: str, now_iso: str) -> dict:
    """构造空排产计划响应。"""
    return {
        "plan_id": 0,
        "plan_version": 0,
        "allocations": [],
        "description": description,
        "status": "EMPTY",
        "created_at": now_iso,
    }


_TRUNCATE_SUFFIX = "...(截断)"


def _truncate(text: str, max_chars: int) -> str:
    """截断文本以避免 prompt 过长，保证返回长度不超过 max_chars。"""
    if len(text) <= max_chars:
        return text
    if max_chars <= len(_TRUNCATE_SUFFIX):
        return text[:max_chars]
    return text[: max_chars - len(_TRUNCATE_SUFFIX)] + _TRUNCATE_SUFFIX


def _now_iso() -> str:
    """返回当前 UTC ISO 字符串。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
