"""文档元数据 PostgreSQL 存储（P0-5：从 doc_meta.json 迁移到 PG）。

使用 asyncpg 连接池，与 B1 async 重构对齐。
多副本部署时各副本共享同一 PG，避免文件持久化导致的元数据不一致。
"""

from datetime import datetime, timezone

from shared.db import get_pg_pool


async def save_doc_meta(doc_id: str, doc_name: str) -> None:
    """插入或更新文档元数据（UPSERT）。"""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO doc_meta (doc_id, doc_name, create_time) VALUES ($1, $2, $3) "
            "ON CONFLICT (doc_id) DO UPDATE SET doc_name = $2",
            doc_id,
            doc_name,
            datetime.now(timezone.utc).replace(tzinfo=None),
        )


async def list_doc_meta() -> dict[str, dict]:
    """返回 {doc_id: {doc_name, create_time}}。"""
    pool = await get_pg_pool()
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
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM doc_meta WHERE doc_id = $1", doc_id)
