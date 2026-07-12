"""订单与排产计划 PostgreSQL 存储。

使用 asyncpg 连接池，复用 shared.db 的公共连接池：
- shared.db.get_pg_pool() 双重检查 + asyncio.Lock 懒初始化；
- 多副本部署时共享同一 PG 实例；
- close_pool() 仅供测试使用，委托 shared.db.close_pool。

涉及两张表：
- production_orders：订单数据
- production_plans：排产计划
DDL 见 database/init/01-schema.sql。
"""

import json
from datetime import datetime, timezone

import asyncpg

from shared.db import close_pool as _shared_close_pool
from shared.db import fmt_ts
from shared.db import get_pg_pool


async def save_order(
    order_no: str,
    product_model: str,
    quantity: int,
    priority: str,
    delivery_date: str,
    material_ready: bool,
    source: str = "user",
) -> int:
    """插入订单，返回新生成的 order_id。

    Args:
        order_no: 订单编号（唯一）。
        product_model: 产品型号。
        quantity: 订单数量。
        priority: 优先级（URGENT/HIGH/NORMAL/LOW）。
        delivery_date: 交付日期（ISO 日期 YYYY-MM-DD）。
        material_ready: 物料是否齐套。
        source: 订单来源（user/orchestrator_synthetic），用于追溯合成急单。

    Returns:
        新生成的 order_id。

    Raises:
        ValueError: delivery_date 格式不符 YYYY-MM-DD。
        asyncpg.exceptions.UniqueViolationError: order_no 已存在（由调用方处理）。
    """
    delivery = _parse_date(delivery_date)
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO production_orders "
            "(order_no, product_model, quantity, priority, delivery_date, "
            "material_ready, status, source) "
            "VALUES ($1, $2, $3, $4, $5, $6, 'PENDING', $7) "
            "RETURNING order_id",
            order_no,
            product_model,
            quantity,
            priority,
            delivery,
            material_ready,
            source,
        )
    return int(row["order_id"])


async def list_orders(status: str | None = None) -> list[dict]:
    """查询订单列表。

    Args:
        status: 可选状态过滤（如 "PENDING"）。不传则返回全部。

    Returns:
        按 delivery_date 升序排列的订单 dict 列表，字段名与数据库列名一致。
    """
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if status:
            rows = await conn.fetch(
                "SELECT order_id, order_no, product_model, quantity, priority, "
                "delivery_date, material_ready, status, source, created_at, "
                "updated_at FROM production_orders WHERE status = $1 "
                "ORDER BY delivery_date ASC",
                status,
            )
        else:
            rows = await conn.fetch(
                "SELECT order_id, order_no, product_model, quantity, priority, "
                "delivery_date, material_ready, status, source, created_at, "
                "updated_at FROM production_orders ORDER BY delivery_date ASC"
            )
    return [_row_to_dict(r) for r in rows]


async def update_order_status(order_id: int, status: str) -> None:
    """更新订单状态。

    Args:
        order_id: 订单 ID。
        status: 新状态（如 "PLANNED"）。
    """
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE production_orders SET status = $1, updated_at = $2 "
            "WHERE order_id = $3",
            status,
            datetime.now(timezone.utc).replace(tzinfo=None),
            order_id,
        )


async def save_plan(
    allocations: list[dict], description: str, plan_version: int
) -> int:
    """保存排产计划，返回新生成的 plan_id。

    先将既有 ACTIVE 计划归档为 ARCHIVED，再插入新计划（status=ACTIVE）。

    Args:
        allocations: 分配项 dict 列表（每项含 order_no/product_model/device_id/
            device_name/start_hour/duration_hours）。
        description: LLM 生成的排产说明文本。
        plan_version: 计划版本号。

    Returns:
        新生成的 plan_id。
    """
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # 归档既有 ACTIVE 计划
            await conn.execute(
                "UPDATE production_plans SET status = 'ARCHIVED' "
                "WHERE status = 'ACTIVE'"
            )
            row = await conn.fetchrow(
                "INSERT INTO production_plans "
                "(plan_version, allocations, description, status) "
                "VALUES ($1, $2, $3, 'ACTIVE') "
                "RETURNING plan_id",
                plan_version,
                json.dumps(allocations, ensure_ascii=False),
                description,
            )
    return int(row["plan_id"])


async def get_current_plan() -> dict | None:
    """查询当前 ACTIVE 计划，无则返回 None。

    Returns:
        含 plan_id/plan_version/allocations/description/status/created_at 的 dict。
    """
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT plan_id, plan_version, allocations, description, status, "
            "created_at FROM production_plans WHERE status = 'ACTIVE' "
            "ORDER BY created_at DESC LIMIT 1"
        )
    if row is None:
        return None
    return _plan_row_to_dict(row)


async def get_next_plan_version() -> int:
    """查询下一个计划版本号（MAX(plan_version)+1）。"""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COALESCE(MAX(plan_version), 0) + 1 AS next_version "
            "FROM production_plans"
        )
    return int(row["next_version"])


async def close_pool() -> None:
    """关闭连接池（仅供测试使用，委托 shared.db.close_pool）。"""
    await _shared_close_pool()


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _parse_date(delivery_date: str):
    """将 YYYY-MM-DD 字符串解析为 date 对象，供 asyncpg 写入 DATE 列。

    Raises:
        ValueError: 格式不符。
    """
    from datetime import datetime

    try:
        return datetime.strptime(delivery_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("delivery_date 格式应为 YYYY-MM-DD") from exc


def _row_to_dict(row: asyncpg.Record) -> dict:
    """将 production_orders 行转为 dict，date/timestamp 字段转字符串。"""
    return {
        "order_id": int(row["order_id"]),
        "order_no": row["order_no"],
        "product_model": row["product_model"],
        "quantity": int(row["quantity"]),
        "priority": row["priority"],
        "delivery_date": row["delivery_date"].strftime("%Y-%m-%d")
        if row["delivery_date"]
        else "",
        "material_ready": bool(row["material_ready"]),
        "status": row["status"],
        "source": row["source"],
        "created_at": fmt_ts(row["created_at"]),
        "updated_at": fmt_ts(row["updated_at"]),
    }


def _plan_row_to_dict(row: asyncpg.Record) -> dict:
    """将 production_plans 行转为 dict，allocations 反序列化为 list。"""
    raw_allocations = row["allocations"]
    if isinstance(raw_allocations, str):
        allocations = json.loads(raw_allocations)
    elif isinstance(raw_allocations, (list, dict)):
        allocations = raw_allocations
    else:
        allocations = []
    return {
        "plan_id": int(row["plan_id"]),
        "plan_version": int(row["plan_version"]),
        "allocations": allocations,
        "description": row["description"] or "",
        "status": row["status"],
        "created_at": fmt_ts(row["created_at"]),
    }

