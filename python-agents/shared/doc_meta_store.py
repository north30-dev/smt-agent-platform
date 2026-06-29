"""文档元数据 PostgreSQL 存储（P0-5：从 doc_meta.json 迁移到 PG）。

使用 asyncpg 连接池，与 B1 async 重构对齐。
多副本部署时各副本共享同一 PG，避免文件持久化导致的元数据不一致。
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


async def save_doc_meta(doc_id: str, doc_name: str) -> None:
    """插入或更新文档元数据（UPSERT）。"""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO doc_meta (doc_id, doc_name, create_time) VALUES ($1, $2, $3) "
            "ON CONFLICT (doc_id) DO UPDATE SET doc_name = $2",
            doc_id,
            doc_name,
            datetime.now(timezone.utc),
        )


async def list_doc_meta() -> dict[str, dict]:
    """返回 {doc_id: {doc_name, create_time}}。"""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT doc_id, doc_name, create_time FROM doc_meta"
        )
    return {
        r["doc_id"]: {
            "doc_name": r["doc_name"],
            "create_time": r["create_time"].strftime("%Y-%m-%dT%H:%M:%SZ")
            if r["create_time"]
            else "",
        }
        for r in rows
    }


async def remove_doc_meta(doc_id: str) -> None:
    """删除指定 doc_id 的元数据。"""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM doc_meta WHERE doc_id = $1", doc_id)
