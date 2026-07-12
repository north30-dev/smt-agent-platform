"""PostgreSQL 连接池与工作流持久化公共模块（CONC-1 / DRY-1 / REL-1）。

提供 asyncpg 连接池的线程安全懒初始化，供 doc_meta_store /
order_store / alert_store / orchestrator 共用，消除三处独立的
`global _pool` TOCTOU 竞态。

同时提供 orchestrator 工作流表的 DDL 初始化与 UPSERT/查询接口，
将工作流状态从内存 dict 迁移到 PostgreSQL，进程重启不丢失。
"""

import asyncio
import json
from datetime import datetime, timezone

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


# ===========================================================================
# Phase 4 执行闭环表：execution_instructions / exception_records / approvals
#
# 三张表均由 init_execution_tables() 幂等创建，DDL 见 database/init/01-schema.sql。
# CRUD 遵循 init_workflow_table / save_workflow / get_workflow 模式：
# - 通过共享 get_pg_pool() 获取连接池；
# - JSONB 字段 json.dumps(ensure_ascii=False) + $N::jsonb 显式转换；
# - 返回 dict 中 timestamp 字段统一格式化为带时区 ISO 字符串。
# ===========================================================================


# ---------------------------------------------------------------------------
# 初始化
# ---------------------------------------------------------------------------


async def init_execution_tables() -> None:
    """幂等创建 Phase 4 执行闭环三张表与索引。

    供 agent-execution 启动时调用；表已存在时无副作用。
    遵循 init_workflow_table 模式：CREATE TABLE IF NOT EXISTS + CREATE INDEX IF NOT EXISTS。
    """
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        # execution_instructions
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS execution_instructions ("
            "id BIGSERIAL PRIMARY KEY, "
            "instruction_id VARCHAR(64) NOT NULL UNIQUE, "
            "source_workflow_id VARCHAR(64), "
            "type VARCHAR(32) NOT NULL, "
            "payload JSONB NOT NULL, "
            "status VARCHAR(32) NOT NULL DEFAULT 'PENDING', "
            "priority VARCHAR(16) NOT NULL DEFAULT 'MEDIUM', "
            "auto_execute BOOLEAN NOT NULL DEFAULT FALSE, "
            "created_at TIMESTAMP NOT NULL DEFAULT NOW(), "
            "updated_at TIMESTAMP NOT NULL DEFAULT NOW()"
            ")"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_execution_instructions_source_workflow_id "
            "ON execution_instructions(source_workflow_id)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_execution_instructions_status "
            "ON execution_instructions(status)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_execution_instructions_type "
            "ON execution_instructions(type)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_execution_instructions_priority "
            "ON execution_instructions(priority)"
        )

        # exception_records
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS exception_records ("
            "id BIGSERIAL PRIMARY KEY, "
            "exception_id VARCHAR(64) NOT NULL UNIQUE, "
            "source VARCHAR(64) NOT NULL, "
            "instruction_id VARCHAR(64), "
            "description TEXT NOT NULL, "
            "status VARCHAR(32) NOT NULL DEFAULT 'OPEN', "
            "analysis JSONB, "
            "created_at TIMESTAMP NOT NULL DEFAULT NOW(), "
            "updated_at TIMESTAMP NOT NULL DEFAULT NOW()"
            ")"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_exception_records_status "
            "ON exception_records(status)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_exception_records_instruction_id "
            "ON exception_records(instruction_id)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_exception_records_source "
            "ON exception_records(source)"
        )

        # approvals
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS approvals ("
            "id BIGSERIAL PRIMARY KEY, "
            "instruction_id VARCHAR(64) NOT NULL, "
            "decision VARCHAR(16) NOT NULL, "
            "approver VARCHAR(64), "
            "comment TEXT, "
            "created_at TIMESTAMP NOT NULL DEFAULT NOW()"
            ")"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_approvals_instruction_id "
            "ON approvals(instruction_id)"
        )


# ---------------------------------------------------------------------------
# execution_instructions CRUD
# ---------------------------------------------------------------------------


async def create_instruction(
    instruction_id: str,
    source_workflow_id: str | None,
    type: str,
    payload: dict,
    status: str = "PENDING",
    priority: str = "MEDIUM",
    auto_execute: bool = False,
) -> dict:
    """插入执行指令记录，返回新记录 dict。

    Args:
        instruction_id: 业务指令 ID（唯一）。
        source_workflow_id: 来源 orchestrator 工作流 ID，人工创建时为 None。
        type: 指令类型 REPAIR / PRODUCTION_ADJUST / PARAM_CHANGE。
        payload: 指令载荷 dict，结构因 type 而异，序列化为 JSONB。
        status: 初始状态，默认 PENDING。
        priority: 优先级 LOW / MEDIUM / CRITICAL。
        auto_execute: 是否自动执行（无需人工审批）。

    Returns:
        新插入记录的完整字段 dict（payload 反序列化为 dict，时间字段为 ISO 字符串）。
    """
    pool = await get_pg_pool()
    payload_json = json.dumps(payload, ensure_ascii=False)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO execution_instructions "
            "(instruction_id, source_workflow_id, type, payload, status, "
            "priority, auto_execute) "
            "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7) "
            "RETURNING id, instruction_id, source_workflow_id, type, payload, "
            "status, priority, auto_execute, created_at, updated_at",
            instruction_id,
            source_workflow_id,
            type,
            payload_json,
            status,
            priority,
            auto_execute,
        )
    return _instruction_row_to_dict(row)


async def get_instruction(instruction_id: str) -> dict | None:
    """按 instruction_id 查询指令，不存在返回 None。"""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, instruction_id, source_workflow_id, type, payload, status, "
            "priority, auto_execute, created_at, updated_at "
            "FROM execution_instructions WHERE instruction_id = $1",
            instruction_id,
        )
    if row is None:
        return None
    return _instruction_row_to_dict(row)


async def list_instructions(
    page: int = 1,
    size: int = 20,
    status: str | None = None,
    instruction_type: str | None = None,
) -> dict:
    """分页查询指令记录，按 created_at DESC 排序。

    遵循 alert_store.list_alerts 分页模式：返回 {records, total, page, size}。
    可选 status / instruction_type 过滤；page 从 1 开始，size<1 归一为 1。

    Args:
        page: 页码，从 1 开始。
        size: 每页条数。
        status: 可选状态过滤（如 PENDING / COMPLETED）。
        instruction_type: 可选类型过滤（如 REPAIR / PARAM_CHANGE）。

    Returns:
        {records: [...], total: int, page: int, size: int}
    """
    if page < 1:
        page = 1
    if size < 1:
        size = 1
    offset = (page - 1) * size

    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        conditions: list[str] = []
        params: list = []
        if status is not None:
            params.append(status)
            conditions.append(f"status = ${len(params)}")
        if instruction_type is not None:
            params.append(instruction_type)
            conditions.append(f"type = ${len(params)}")
        where_clause = (
            " WHERE " + " AND ".join(conditions) if conditions else ""
        )

        total_row = await conn.fetchrow(
            f"SELECT COUNT(*) AS cnt FROM execution_instructions{where_clause}",
            *params,
        )
        total = int(total_row["cnt"])

        limit_idx = len(params) + 1
        offset_idx = len(params) + 2
        rows = await conn.fetch(
            "SELECT id, instruction_id, source_workflow_id, type, payload, status, "
            "priority, auto_execute, created_at, updated_at "
            f"FROM execution_instructions{where_clause} "
            f"ORDER BY created_at DESC LIMIT ${limit_idx} OFFSET ${offset_idx}",
            *params,
            size,
            offset,
        )

    records = [_instruction_row_to_dict(r) for r in rows]
    return {
        "records": records,
        "total": total,
        "page": page,
        "size": size,
    }


async def update_instruction_status(
    instruction_id: str,
    status: str,
    note: str | None = None,
) -> dict | None:
    """更新指令状态，返回更新后的记录；指令不存在返回 None。

    note 参数用于调用方传递备注（当前 schema 无 note 列，仅更新 status + updated_at）。

    Args:
        instruction_id: 指令 ID。
        status: 新状态。
        note: 备注文本，当前不持久化（预留扩展）。

    Returns:
        更新后的记录 dict，或 None。
    """
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE execution_instructions "
            "SET status = $1, updated_at = NOW() "
            "WHERE instruction_id = $2 "
            "RETURNING id, instruction_id, source_workflow_id, type, payload, "
            "status, priority, auto_execute, created_at, updated_at",
            status,
            instruction_id,
        )
    if row is None:
        return None
    return _instruction_row_to_dict(row)


# ---------------------------------------------------------------------------
# exception_records CRUD
# ---------------------------------------------------------------------------


async def create_exception(
    exception_id: str,
    source: str,
    instruction_id: str | None,
    description: str,
) -> dict:
    """插入异常记录，status 默认 OPEN，返回新记录 dict。

    Args:
        exception_id: 异常业务 ID（唯一）。
        source: 来源（instruction_timeout / kafka_event / manual）。
        instruction_id: 关联指令 ID，可空。
        description: 异常描述。

    Returns:
        新插入记录的完整字段 dict。
    """
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO exception_records "
            "(exception_id, source, instruction_id, description) "
            "VALUES ($1, $2, $3, $4) "
            "RETURNING id, exception_id, source, instruction_id, description, "
            "status, analysis, created_at, updated_at",
            exception_id,
            source,
            instruction_id,
            description,
        )
    return _exception_row_to_dict(row)


async def get_exception(exception_id: str) -> dict | None:
    """按 exception_id 查询异常，不存在返回 None。"""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, exception_id, source, instruction_id, description, "
            "status, analysis, created_at, updated_at "
            "FROM exception_records WHERE exception_id = $1",
            exception_id,
        )
    if row is None:
        return None
    return _exception_row_to_dict(row)


async def list_exceptions(
    page: int = 1,
    size: int = 20,
    status: str | None = None,
) -> dict:
    """分页查询异常记录，按 created_at DESC 排序，可选 status 过滤。

    遵循 alert_store.list_alerts 分页模式：返回 {records, total, page, size}。

    Args:
        page: 页码，从 1 开始。
        size: 每页条数。
        status: 可选状态过滤（如 OPEN / ANALYZED / CLOSED）。

    Returns:
        {records: [...], total: int, page: int, size: int}
    """
    if page < 1:
        page = 1
    if size < 1:
        size = 1
    offset = (page - 1) * size

    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if status is not None:
            total_row = await conn.fetchrow(
                "SELECT COUNT(*) AS cnt FROM exception_records WHERE status = $1",
                status,
            )
            rows = await conn.fetch(
                "SELECT id, exception_id, source, instruction_id, description, "
                "status, analysis, created_at, updated_at "
                "FROM exception_records WHERE status = $1 "
                "ORDER BY created_at DESC LIMIT $2 OFFSET $3",
                status,
                size,
                offset,
            )
        else:
            total_row = await conn.fetchrow(
                "SELECT COUNT(*) AS cnt FROM exception_records"
            )
            rows = await conn.fetch(
                "SELECT id, exception_id, source, instruction_id, description, "
                "status, analysis, created_at, updated_at "
                "FROM exception_records "
                "ORDER BY created_at DESC LIMIT $1 OFFSET $2",
                size,
                offset,
            )

    total = int(total_row["cnt"])
    records = [_exception_row_to_dict(r) for r in rows]
    return {
        "records": records,
        "total": total,
        "page": page,
        "size": size,
    }


async def update_exception_status(
    exception_id: str,
    status: str,
    analysis: dict | None = None,
) -> dict | None:
    """更新异常状态，可选写入 analysis 分析结果；异常不存在返回 None。

    用于 analyze（status=ANALYZED + analysis）与 verify（status=CLOSED 或回退 OPEN）。

    Args:
        exception_id: 异常 ID。
        status: 新状态（如 ANALYZED / HANDLED / CLOSED）。
        analysis: LLM 分析结果 dict，None 时仅更新 status。

    Returns:
        更新后的记录 dict，或 None。
    """
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if analysis is not None:
            analysis_json = json.dumps(analysis, ensure_ascii=False)
            row = await conn.fetchrow(
                "UPDATE exception_records "
                "SET status = $1, analysis = $2::jsonb, updated_at = NOW() "
                "WHERE exception_id = $3 "
                "RETURNING id, exception_id, source, instruction_id, description, "
                "status, analysis, created_at, updated_at",
                status,
                analysis_json,
                exception_id,
            )
        else:
            row = await conn.fetchrow(
                "UPDATE exception_records "
                "SET status = $1, updated_at = NOW() "
                "WHERE exception_id = $2 "
                "RETURNING id, exception_id, source, instruction_id, description, "
                "status, analysis, created_at, updated_at",
                status,
                exception_id,
            )
    if row is None:
        return None
    return _exception_row_to_dict(row)


# ---------------------------------------------------------------------------
# approvals CRUD
# ---------------------------------------------------------------------------


async def create_approval(
    instruction_id: str,
    decision: str,
    approver: str | None,
    comment: str | None,
) -> dict:
    """插入审批记录，返回新记录 dict。

    Args:
        instruction_id: 关联指令 ID。
        decision: 审批决定 APPROVE / REJECT。
        approver: 审批人，可空。
        comment: 审批意见，可空。

    Returns:
        新插入记录的完整字段 dict。
    """
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO approvals "
            "(instruction_id, decision, approver, comment) "
            "VALUES ($1, $2, $3, $4) "
            "RETURNING id, instruction_id, decision, approver, comment, created_at",
            instruction_id,
            decision,
            approver,
            comment,
        )
    return _approval_row_to_dict(row)


async def update_instruction_status_and_create_approval(
    instruction_id: str,
    new_status: str,
    decision: str,
    approver: str | None,
    comment: str | None,
) -> dict | None:
    """事务内更新指令状态 + 写入审批记录，保证原子性。

    Args:
        instruction_id: 指令 ID。
        new_status: 目标状态（如 APPROVED / REJECTED）。
        decision: 审批决定。
        approver: 审批人。
        comment: 审批意见。

    Returns:
        更新后的指令记录 dict，或 None（指令不存在）。
    """
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "UPDATE execution_instructions "
                "SET status = $1, updated_at = NOW() "
                "WHERE instruction_id = $2 "
                "RETURNING id, instruction_id, source_workflow_id, type, payload, "
                "status, priority, auto_execute, created_at, updated_at",
                new_status,
                instruction_id,
            )
            if row is None:
                return None
            await conn.execute(
                "INSERT INTO approvals "
                "(instruction_id, decision, approver, comment) "
                "VALUES ($1, $2, $3, $4)",
                instruction_id,
                decision,
                approver,
                comment,
            )
    return _instruction_row_to_dict(row)


async def get_approvals_by_instruction(instruction_id: str) -> list[dict]:
    """查询某指令的全部审批记录，按 created_at 升序返回。

    Args:
        instruction_id: 指令 ID。

    Returns:
        审批记录 dict 列表，可能为空。
    """
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, instruction_id, decision, approver, comment, created_at "
            "FROM approvals WHERE instruction_id = $1 "
            "ORDER BY created_at ASC",
            instruction_id,
        )
    return [_approval_row_to_dict(r) for r in rows]


# ===========================================================================
# Phase 4 行转 dict 辅助函数
#
# 遵循 alert_store._row_to_dict / order_store.fmt_ts 模式：
# - JSONB 字段兼容 str（asyncpg 默认返回 str）/ dict / list；
# - timestamp 字段统一为带时区的 ISO 字符串。
# ===========================================================================


def parse_jsonb(raw) -> dict | list | None:
    """JSONB 字段反序列化：兼容 str / dict / list / None。"""
    if raw is None:
        return None
    if isinstance(raw, str):
        return json.loads(raw)
    if isinstance(raw, (dict, list)):
        return raw
    return None


def fmt_ts(ts) -> str:
    """timestamp 格式化为带时区的 ISO 字符串。

    无时区信息时按 UTC 处理，与 alert_store._row_to_dict 对齐。
    """
    if ts is None:
        return ""
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.isoformat()
    return str(ts)


def _instruction_row_to_dict(row: asyncpg.Record) -> dict:
    """execution_instructions 行转 dict。"""
    return {
        "id": int(row["id"]),
        "instruction_id": row["instruction_id"],
        "source_workflow_id": row["source_workflow_id"],
        "type": row["type"],
        "payload": parse_jsonb(row["payload"]),
        "status": row["status"],
        "priority": row["priority"],
        "auto_execute": bool(row["auto_execute"]),
        "created_at": fmt_ts(row["created_at"]),
        "updated_at": fmt_ts(row["updated_at"]),
    }


def _exception_row_to_dict(row: asyncpg.Record) -> dict:
    """exception_records 行转 dict。"""
    return {
        "id": int(row["id"]),
        "exception_id": row["exception_id"],
        "source": row["source"],
        "instruction_id": row["instruction_id"],
        "description": row["description"],
        "status": row["status"],
        "analysis": parse_jsonb(row["analysis"]),
        "created_at": fmt_ts(row["created_at"]),
        "updated_at": fmt_ts(row["updated_at"]),
    }


def _approval_row_to_dict(row: asyncpg.Record) -> dict:
    """approvals 行转 dict。"""
    return {
        "id": int(row["id"]),
        "instruction_id": row["instruction_id"],
        "decision": row["decision"],
        "approver": row["approver"],
        "comment": row["comment"],
        "created_at": fmt_ts(row["created_at"]),
    }
