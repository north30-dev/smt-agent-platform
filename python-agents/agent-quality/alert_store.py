"""质量告警记录 PostgreSQL 存储。

使用 asyncpg 连接池，与 shared.doc_meta_store 模式对齐。
多副本部署时各副本共享同一 PG，避免告警丢失。
错误不在本模块捕获，统一交由 main.py 异常处理器兜底。
"""

from datetime import datetime, timezone

import asyncpg

from shared.config import settings

# 模块级连接池（懒初始化）
_pool: asyncpg.Pool | None = None


async def _get_pool() -> asyncpg.Pool:
    """懒初始化 asyncpg 连接池。"""
    global _pool
    if _pool is not None:
        return _pool
    _pool = await asyncpg.create_pool(
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
        min_size=1,
        max_size=5,
    )
    return _pool


async def save_alert(
    device_id: int,
    defect_rate: float,
    threshold: float,
    status: str,
    datapoint_code: str | None,
) -> int:
    """写入一条质量告警记录。

    Args:
        device_id: 设备 ID。
        defect_rate: 触发告警时的缺陷率均值。
        threshold: 触发告警时的阈值。
        status: 告警状态（ALERT）。
        datapoint_code: 采集点编码，可空。

    Returns:
        新插入记录的自增 id。
    """
    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO quality_alerts "
            "(device_id, defect_rate, threshold, status, datapoint_code, alert_time) "
            "VALUES ($1, $2, $3, $4, $5, $6) "
            "RETURNING id",
            device_id,
            defect_rate,
            threshold,
            status,
            datapoint_code,
            datetime.now(timezone.utc),
        )
    return int(row["id"])


async def list_alerts(page: int = 1, size: int | None = None) -> dict:
    """分页查询质量告警，按 alert_time DESC 排序。

    Args:
        page: 页码，从 1 开始。
        size: 每页条数，None 时取 settings.quality_alerts_page_size。

    Returns:
        {records, total, page, size}
    """
    if page < 1:
        page = 1
    if size is None:
        size = settings.quality_alerts_page_size
    if size < 1:
        size = 1
    offset = (page - 1) * size

    pool = await _get_pool()
    async with pool.acquire() as conn:
        total_row = await conn.fetchrow(
            "SELECT COUNT(*) AS cnt FROM quality_alerts"
        )
        total = int(total_row["cnt"])
        rows = await conn.fetch(
            "SELECT id, device_id, defect_rate, threshold, status, "
            "datapoint_code, alert_time "
            "FROM quality_alerts "
            "ORDER BY alert_time DESC LIMIT $1 OFFSET $2",
            size,
            offset,
        )

    records = [_row_to_dict(r) for r in rows]
    return {
        "records": records,
        "total": total,
        "page": page,
        "size": size,
    }


def _row_to_dict(row) -> dict:
    """asyncpg.Record 转 dict，alert_time 格式化为 ISO 字符串。"""
    alert_time = row["alert_time"]
    if alert_time is None:
        alert_time_str = ""
    elif isinstance(alert_time, datetime):
        # 统一输出带时区的 ISO 字符串
        if alert_time.tzinfo is None:
            alert_time = alert_time.replace(tzinfo=timezone.utc)
        alert_time_str = alert_time.isoformat()
    else:
        alert_time_str = str(alert_time)

    return {
        "id": int(row["id"]),
        "device_id": int(row["device_id"]),
        "defect_rate": float(row["defect_rate"]),
        "threshold": float(row["threshold"]),
        "status": str(row["status"]),
        "datapoint_code": row["datapoint_code"],
        "alert_time": alert_time_str,
    }


async def close_pool() -> None:
    """关闭连接池（仅供测试清理使用）。"""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
