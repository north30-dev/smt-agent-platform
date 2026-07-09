"""PostgreSQL 连接池与工作流持久化公共模块（CONC-1 / DRY-1 / REL-1）。

提供 asyncpg 连接池的线程安全懒初始化，供 doc_meta_store /
order_store / alert_store / orchestrator 共用，消除三处独立的
`global _pool` TOCTOU 竞态。

同时提供 orchestrator 工作流表的 DDL 初始化与 UPSERT/查询接口，
将工作流状态从内存 dict 迁移到 PostgreSQL，进程重启不丢失。
"""

import asyncio
import json

import asyncpg

from shared.config import settings

# 模块级连接池（懒初始化）+ 锁，保证并发首次调用仅创建一个池
_pool: asyncpg.Pool | None = None
_pool_lock = asyncio.Lock()


async def get_pg_pool() -> asyncpg.Pool:
    """获取共享 asyncpg 连接池（双重检查 + asyncio.Lock 懒初始化）。

    多协程并发首次调用时，仅创建一个连接池实例，无实例被覆盖泄漏。
    使用 settings.postgres_* 配置，min_size=1 / max_size=5。
    """
    global _pool
    if _pool is not None:
        return _pool
    async with _pool_lock:
        # 持锁后二次检查，避免锁等待期间已被其他协程初始化
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


async def init_workflow_table() -> None:
    """幂等创建 workflows 表与索引。

    供 orchestrator 启动时调用；表已存在时无副作用。
    """
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS workflows ("
            "workflow_id VARCHAR(64) PRIMARY KEY, "
            "status VARCHAR(16) NOT NULL, "
            "data JSONB NOT NULL, "
            "created_at TIMESTAMP DEFAULT NOW()"
            ")"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_workflows_created_at "
            "ON workflows(created_at)"
        )


async def save_workflow(workflow_id: str, status: str, data: dict) -> None:
    """UPSERT 工作流记录。

    Args:
        workflow_id: 工作流 ID。
        status: 工作流状态（如 RUNNING / COMPLETED / FAILED）。
        data: 工作流数据 dict，序列化为 JSONB 存储。
    """
    pool = await get_pg_pool()
    payload = json.dumps(data, ensure_ascii=False)
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO workflows (workflow_id, status, data) "
            "VALUES ($1, $2, $3::jsonb) "
            "ON CONFLICT (workflow_id) DO UPDATE SET "
            "status = $2, data = $3::jsonb",
            workflow_id,
            status,
            payload,
        )


async def get_workflow(workflow_id: str) -> dict | None:
    """查询工作流记录。

    Args:
        workflow_id: 工作流 ID。

    Returns:
        {"workflow_id": ..., "status": ..., **<data>} 或 None（不存在）。
    """
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT workflow_id, status, data FROM workflows "
            "WHERE workflow_id = $1",
            workflow_id,
        )
    if row is None:
        return None
    raw_data = row["data"]
    if isinstance(raw_data, str):
        data = json.loads(raw_data)
    else:
        data = raw_data if isinstance(raw_data, (dict, list)) else {}
    return {
        "workflow_id": row["workflow_id"],
        "status": row["status"],
        **(data if isinstance(data, dict) else {"data": data}),
    }


async def close_pool() -> None:
    """关闭共享连接池（供测试与进程 shutdown 使用）。

    幂等：池不存在时直接返回。
    """
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
