"""Phase 4 执行闭环表 CRUD 单元测试（shared.db.execution_*）。

不触达真实 PostgreSQL：通过 monkeypatch 替换 shared.db.get_pg_pool，
返回 FakePool，其 acquire() 产出 FakeConn（execute/fetchrow/fetch 为 AsyncMock）。
各用例按需配置 FakeConn.fetchrow/fetch 的返回值，验证：
1. SQL 语句包含正确的表名 / 列名 / 占位符；
2. 传入参数顺序与值正确；
3. 返回 dict 的字段映射、JSONB 反序列化、timestamp ISO 格式化。

遵循现有 test_quality_api.py / test_orchestrator_api.py 风格：
- async def 测试函数（pyproject.toml asyncio_mode=auto）；
- 不依赖真实 PG 实例。
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from shared import db as shared_db


# ---------------------------------------------------------------------------
# asyncpg 假对象：FakeRecord / FakeConn / FakePool
# ---------------------------------------------------------------------------


class FakeRecord:
    """asyncpg.Record-like：支持 row["col"] 下标访问。

    asyncpg.Record 同时支持整数下标与列名下标；此处仅实现列名下标，
    覆盖 shared.db 中所有 _row_to_dict 的访问路径。
    """

    def __init__(self, **fields):
        self._fields = fields

    def __getitem__(self, key):
        return self._fields[key]

    def keys(self):
        return self._fields.keys()


class FakeConn:
    """asyncpg.Connection-like：execute/fetchrow/fetch 均为 AsyncMock。

    各用例通过设置 conn.fetchrow.return_value / conn.fetch.return_value
    或 side_effect 来控制返回值。
    """

    def __init__(self):
        self.execute = AsyncMock()
        self.fetchrow = AsyncMock()
        self.fetch = AsyncMock()


class FakePool:
    """asyncpg.Pool-like：acquire() 返回 async context manager，yield 单一 FakeConn。"""

    def __init__(self):
        self.conn = FakeConn()
        self.closed = False

    @asynccontextmanager
    async def acquire(self):
        yield self.conn

    async def close(self):
        self.closed = True


# ---------------------------------------------------------------------------
# 公共 fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_shared_pool():
    """每个用例前后重置 shared.db 模块级连接池，避免跨用例污染。"""
    shared_db._pool = None
    yield
    shared_db._pool = None


@pytest.fixture
def fake_pool(monkeypatch):
    """替换 shared.db.get_pg_pool 为返回 FakePool 的 AsyncMock。

    shared.db 内 CRUD 函数以裸名 get_pg_pool() 调用，
    monkeypatch 替换模块属性后即可生效。
    """
    pool = FakePool()
    monkeypatch.setattr(
        shared_db, "get_pg_pool", AsyncMock(return_value=pool)
    )
    return pool


def _ts(minute_offset: int = 0) -> datetime:
    """构造带时区的固定时间戳，便于断言 ISO 字符串。"""
    base = datetime(2026, 7, 9, 10, 0, 0, tzinfo=timezone.utc)
    return base + _minute(minute_offset)


def _minute(minutes: int):
    from datetime import timedelta

    return timedelta(minutes=minutes)


# ---------------------------------------------------------------------------
# init_execution_tables
# ---------------------------------------------------------------------------


async def test_init_execution_tables_creates_all_tables_and_indexes(fake_pool):
    """init_execution_tables 应对三张表与索引执行 CREATE IF NOT EXISTS。"""
    await shared_db.init_execution_tables()

    executes = fake_pool.conn.execute.call_args_list
    sqls = [c.args[0] for c in executes]

    # 三张表
    assert any("CREATE TABLE IF NOT EXISTS execution_instructions" in s for s in sqls)
    assert any("CREATE TABLE IF NOT EXISTS exception_records" in s for s in sqls)
    assert any("CREATE TABLE IF NOT EXISTS approvals" in s for s in sqls)
    # execution_instructions 四个索引
    assert any("idx_execution_instructions_source_workflow_id" in s for s in sqls)
    assert any("idx_execution_instructions_status" in s for s in sqls)
    assert any("idx_execution_instructions_type" in s for s in sqls)
    assert any("idx_execution_instructions_priority" in s for s in sqls)
    # exception_records 三个索引
    assert any("idx_exception_records_status" in s for s in sqls)
    assert any("idx_exception_records_instruction_id" in s for s in sqls)
    assert any("idx_exception_records_source" in s for s in sqls)
    # approvals 一个索引
    assert any("idx_approvals_instruction_id" in s for s in sqls)
    # 全部 IF NOT EXISTS（幂等）
    assert all("IF NOT EXISTS" in s for s in sqls)


async def test_init_execution_tables_uses_single_connection(fake_pool):
    """init_execution_tables 应在单个连接内执行所有 DDL（async with pool.acquire()）。"""
    await shared_db.init_execution_tables()

    # execute 被调用多次，但都在同一个 FakeConn 上
    assert fake_pool.conn.execute.await_count == 11  # 3 表 + 8 索引


# ---------------------------------------------------------------------------
# create_instruction
# ---------------------------------------------------------------------------


async def test_create_instruction_inserts_and_returns_dict(fake_pool):
    """create_instruction 应 INSERT 并 RETURNING 全字段，返回 dict。"""
    created_at = _ts(0)
    updated_at = _ts(0)
    fake_pool.conn.fetchrow.return_value = FakeRecord(
        id=1,
        instruction_id="instr-0001",
        source_workflow_id="wf-abc",
        type="REPAIR",
        payload='{"device_id": 1, "action": "replace_head"}',
        status="PENDING",
        priority="CRITICAL",
        auto_execute=False,
        created_at=created_at,
        updated_at=updated_at,
    )

    result = await shared_db.create_instruction(
        instruction_id="instr-0001",
        source_workflow_id="wf-abc",
        type="REPAIR",
        payload={"device_id": 1, "action": "replace_head"},
        status="PENDING",
        priority="CRITICAL",
        auto_execute=False,
    )

    # SQL 校验
    call = fake_pool.conn.fetchrow.call_args
    sql = call.args[0]
    assert "INSERT INTO execution_instructions" in sql
    assert "RETURNING" in sql
    assert "$4::jsonb" in sql  # payload 显式 jsonb 转换

    # 参数校验：payload 应被 json.dumps 序列化
    args = call.args[1:]
    assert args[0] == "instr-0001"
    assert args[1] == "wf-abc"
    assert args[2] == "REPAIR"
    assert '"device_id": 1' in args[3]  # json.dumps ensure_ascii=False
    assert args[3] == '{"device_id": 1, "action": "replace_head"}'
    assert args[4] == "PENDING"
    assert args[5] == "CRITICAL"
    assert args[6] is False

    # 返回 dict 校验
    assert result["id"] == 1
    assert result["instruction_id"] == "instr-0001"
    assert result["source_workflow_id"] == "wf-abc"
    assert result["type"] == "REPAIR"
    assert result["payload"] == {"device_id": 1, "action": "replace_head"}
    assert result["status"] == "PENDING"
    assert result["priority"] == "CRITICAL"
    assert result["auto_execute"] is False
    assert result["created_at"] == created_at.isoformat()
    assert result["updated_at"] == updated_at.isoformat()


async def test_create_instruction_default_args(fake_pool):
    """create_instruction 不传可选参数时应使用默认 status/priority/auto_execute。"""
    fake_pool.conn.fetchrow.return_value = FakeRecord(
        id=2,
        instruction_id="instr-0002",
        source_workflow_id=None,
        type="PARAM_CHANGE",
        payload="{}",
        status="PENDING",
        priority="MEDIUM",
        auto_execute=False,
        created_at=_ts(0),
        updated_at=_ts(0),
    )

    result = await shared_db.create_instruction(
        instruction_id="instr-0002",
        source_workflow_id=None,
        type="PARAM_CHANGE",
        payload={},
    )

    args = fake_pool.conn.fetchrow.call_args.args[1:]
    assert args[4] == "PENDING"
    assert args[5] == "MEDIUM"
    assert args[6] is False
    assert result["source_workflow_id"] is None
    assert result["payload"] == {}


async def test_create_instruction_payload_jsonb_dict_from_db(fake_pool):
    """payload 从 DB 返回为 dict 时（asyncpg 部分配置下）应原样保留。"""
    fake_pool.conn.fetchrow.return_value = FakeRecord(
        id=3,
        instruction_id="instr-0003",
        source_workflow_id=None,
        type="PRODUCTION_ADJUST",
        payload={"line": "L1", "shift": "night"},
        status="PENDING",
        priority="LOW",
        auto_execute=True,
        created_at=_ts(0),
        updated_at=_ts(0),
    )

    result = await shared_db.create_instruction(
        "instr-0003", None, "PRODUCTION_ADJUST", {"line": "L1", "shift": "night"}
    )

    assert result["payload"] == {"line": "L1", "shift": "night"}
    assert result["auto_execute"] is True


async def test_create_instruction_serializes_non_ascii_payload(fake_pool):
    """payload 含中文时 ensure_ascii=False 应保留中文明文。"""
    fake_pool.conn.fetchrow.return_value = FakeRecord(
        id=4,
        instruction_id="instr-0004",
        source_workflow_id=None,
        type="REPAIR",
        payload='{"desc": "更换贴装头"}',
        status="PENDING",
        priority="MEDIUM",
        auto_execute=False,
        created_at=_ts(0),
        updated_at=_ts(0),
    )

    await shared_db.create_instruction(
        "instr-0004", None, "REPAIR", {"desc": "更换贴装头"}
    )

    args = fake_pool.conn.fetchrow.call_args.args[1:]
    assert "更换贴装头" in args[3]
    assert "\\u" not in args[3]  # 未转义


# ---------------------------------------------------------------------------
# get_instruction
# ---------------------------------------------------------------------------


async def test_get_instruction_returns_dict_when_found(fake_pool):
    """get_instruction 命中时返回 dict。"""
    fake_pool.conn.fetchrow.return_value = FakeRecord(
        id=1,
        instruction_id="instr-0001",
        source_workflow_id="wf-abc",
        type="REPAIR",
        payload='{"k": "v"}',
        status="COMPLETED",
        priority="CRITICAL",
        auto_execute=False,
        created_at=_ts(0),
        updated_at=_ts(5),
    )

    result = await shared_db.get_instruction("instr-0001")

    call = fake_pool.conn.fetchrow.call_args
    assert "WHERE instruction_id = $1" in call.args[0]
    assert call.args[1] == "instr-0001"

    assert result is not None
    assert result["instruction_id"] == "instr-0001"
    assert result["status"] == "COMPLETED"
    assert result["payload"] == {"k": "v"}
    assert result["created_at"] == _ts(0).isoformat()
    assert result["updated_at"] == _ts(5).isoformat()


async def test_get_instruction_returns_none_when_not_found(fake_pool):
    """get_instruction 未命中时返回 None。"""
    fake_pool.conn.fetchrow.return_value = None

    result = await shared_db.get_instruction("instr-missing")

    assert result is None


# ---------------------------------------------------------------------------
# list_instructions
# ---------------------------------------------------------------------------


async def test_list_instructions_no_filter(fake_pool):
    """无过滤时分页查询，返回 {records, total, page, size}。"""
    fake_pool.conn.fetchrow.return_value = FakeRecord(cnt=42)
    fake_pool.conn.fetch.return_value = [
        FakeRecord(
            id=i,
            instruction_id=f"instr-{i:04d}",
            source_workflow_id=None,
            type="REPAIR",
            payload="{}",
            status="PENDING",
            priority="MEDIUM",
            auto_execute=False,
            created_at=_ts(i),
            updated_at=_ts(i),
        )
        for i in range(1, 21)
    ]

    result = await shared_db.list_instructions(page=2, size=20)

    # COUNT 不带 WHERE
    count_call = fake_pool.conn.fetchrow.call_args
    assert "SELECT COUNT(*) AS cnt FROM execution_instructions" in count_call.args[0]
    assert "WHERE" not in count_call.args[0]

    # 查询 SQL
    fetch_call = fake_pool.conn.fetch.call_args
    sql = fetch_call.args[0]
    assert "ORDER BY created_at DESC" in sql
    assert "LIMIT $1 OFFSET $2" in sql  # 无过滤时 limit/offset 占 $1/$2
    assert fetch_call.args[1] == 20  # size
    assert fetch_call.args[2] == 20  # offset = (2-1)*20

    assert result["total"] == 42
    assert result["page"] == 2
    assert result["size"] == 20
    assert len(result["records"]) == 20
    assert result["records"][0]["instruction_id"] == "instr-0001"


async def test_list_instructions_with_status_and_type_filter(fake_pool):
    """status + type 双过滤时 WHERE 与占位符顺序正确。"""
    fake_pool.conn.fetchrow.return_value = FakeRecord(cnt=3)
    fake_pool.conn.fetch.return_value = [
        FakeRecord(
            id=1,
            instruction_id="instr-0001",
            source_workflow_id=None,
            type="PARAM_CHANGE",
            payload="{}",
            status="PENDING",
            priority="MEDIUM",
            auto_execute=False,
            created_at=_ts(0),
            updated_at=_ts(0),
        )
    ]

    result = await shared_db.list_instructions(
        page=1, size=10, status="PENDING", instruction_type="PARAM_CHANGE"
    )

    # COUNT SQL 含双 WHERE
    count_call = fake_pool.conn.fetchrow.call_args
    count_sql = count_call.args[0]
    assert "WHERE status = $1 AND type = $2" in count_sql
    assert count_call.args[1] == "PENDING"
    assert count_call.args[2] == "PARAM_CHANGE"

    # 查询 SQL：limit/offset 占位符应为 $3/$4（前两个被 status/type 占用）
    fetch_call = fake_pool.conn.fetch.call_args
    sql = fetch_call.args[0]
    assert "WHERE status = $1 AND type = $2" in sql
    assert "LIMIT $3 OFFSET $4" in sql
    assert fetch_call.args[1] == "PENDING"
    assert fetch_call.args[2] == "PARAM_CHANGE"
    assert fetch_call.args[3] == 10  # size
    assert fetch_call.args[4] == 0  # offset

    assert result["total"] == 3
    assert len(result["records"]) == 1


async def test_list_instructions_status_only_filter(fake_pool):
    """仅 status 过滤时占位符顺序正确（limit/offset 为 $2/$3）。"""
    fake_pool.conn.fetchrow.return_value = FakeRecord(cnt=1)
    fake_pool.conn.fetch.return_value = []

    await shared_db.list_instructions(page=1, size=5, status="COMPLETED")

    fetch_call = fake_pool.conn.fetch.call_args
    assert "WHERE status = $1" in fetch_call.args[0]
    assert "LIMIT $2 OFFSET $3" in fetch_call.args[0]
    assert fetch_call.args[1] == "COMPLETED"
    assert fetch_call.args[2] == 5
    assert fetch_call.args[3] == 0


async def test_list_instructions_normalizes_invalid_page_size(fake_pool):
    """page<1 归一为 1，size<1 归一为 1。"""
    fake_pool.conn.fetchrow.return_value = FakeRecord(cnt=0)
    fake_pool.conn.fetch.return_value = []

    result = await shared_db.list_instructions(page=0, size=0)

    assert result["page"] == 1
    assert result["size"] == 1
    # offset 应为 0
    fetch_call = fake_pool.conn.fetch.call_args
    assert fetch_call.args[-1] == 0  # 最后一个位置参数为 offset


async def test_list_instructions_empty(fake_pool):
    """无记录时返回空 records 与 total=0。"""
    fake_pool.conn.fetchrow.return_value = FakeRecord(cnt=0)
    fake_pool.conn.fetch.return_value = []

    result = await shared_db.list_instructions()

    assert result["records"] == []
    assert result["total"] == 0


# ---------------------------------------------------------------------------
# update_instruction_status
# ---------------------------------------------------------------------------


async def test_update_instruction_status_returns_updated(fake_pool):
    """更新成功返回更新后的记录。"""
    fake_pool.conn.fetchrow.return_value = FakeRecord(
        id=1,
        instruction_id="instr-0001",
        source_workflow_id=None,
        type="REPAIR",
        payload="{}",
        status="COMPLETED",
        priority="MEDIUM",
        auto_execute=False,
        created_at=_ts(0),
        updated_at=_ts(10),
    )

    result = await shared_db.update_instruction_status(
        "instr-0001", "COMPLETED", note="done"
    )

    call = fake_pool.conn.fetchrow.call_args
    sql = call.args[0]
    assert "UPDATE execution_instructions" in sql
    assert "SET status = $1, updated_at = NOW()" in sql
    assert "WHERE instruction_id = $2" in sql
    assert "RETURNING" in sql
    assert call.args[1] == "COMPLETED"
    assert call.args[2] == "instr-0001"

    assert result["status"] == "COMPLETED"
    assert result["updated_at"] == _ts(10).isoformat()


async def test_update_instruction_status_returns_none_when_not_found(fake_pool):
    """指令不存在时 fetchrow 返回 None → 返回 None。"""
    fake_pool.conn.fetchrow.return_value = None

    result = await shared_db.update_instruction_status("instr-missing", "COMPLETED")

    assert result is None


async def test_update_instruction_status_note_optional(fake_pool):
    """note 参数可选，不传时也能正常更新。"""
    fake_pool.conn.fetchrow.return_value = FakeRecord(
        id=1,
        instruction_id="instr-0001",
        source_workflow_id=None,
        type="REPAIR",
        payload="{}",
        status="EXECUTING",
        priority="MEDIUM",
        auto_execute=False,
        created_at=_ts(0),
        updated_at=_ts(1),
    )

    result = await shared_db.update_instruction_status("instr-0001", "EXECUTING")

    assert result["status"] == "EXECUTING"


# ---------------------------------------------------------------------------
# create_exception
# ---------------------------------------------------------------------------


async def test_create_exception_inserts_and_returns_dict(fake_pool):
    """create_exception 应 INSERT 并返回 dict，status 默认 OPEN，analysis 默认 None。"""
    fake_pool.conn.fetchrow.return_value = FakeRecord(
        id=1,
        exception_id="exc-0001",
        source="instruction_timeout",
        instruction_id="instr-0001",
        description="指令执行超时",
        status="OPEN",
        analysis=None,
        created_at=_ts(0),
        updated_at=_ts(0),
    )

    result = await shared_db.create_exception(
        exception_id="exc-0001",
        source="instruction_timeout",
        instruction_id="instr-0001",
        description="指令执行超时",
    )

    call = fake_pool.conn.fetchrow.call_args
    sql = call.args[0]
    assert "INSERT INTO exception_records" in sql
    assert "RETURNING" in sql
    # 不写 status/analysis 列，依赖 DB 默认值
    assert "status" not in sql.split("VALUES")[0].split("INSERT INTO exception_records")[1]
    args = call.args[1:]
    assert args[0] == "exc-0001"
    assert args[1] == "instruction_timeout"
    assert args[2] == "instr-0001"
    assert args[3] == "指令执行超时"

    assert result["id"] == 1
    assert result["exception_id"] == "exc-0001"
    assert result["source"] == "instruction_timeout"
    assert result["instruction_id"] == "instr-0001"
    assert result["description"] == "指令执行超时"
    assert result["status"] == "OPEN"
    assert result["analysis"] is None
    assert result["created_at"] == _ts(0).isoformat()


async def test_create_exception_null_instruction_id(fake_pool):
    """instruction_id 可为 None（kafka_event 来源时无关联指令）。"""
    fake_pool.conn.fetchrow.return_value = FakeRecord(
        id=2,
        exception_id="exc-0002",
        source="kafka_event",
        instruction_id=None,
        description="Kafka 事件触发异常",
        status="OPEN",
        analysis=None,
        created_at=_ts(0),
        updated_at=_ts(0),
    )

    result = await shared_db.create_exception(
        "exc-0002", "kafka_event", None, "Kafka 事件触发异常"
    )

    assert result["instruction_id"] is None


# ---------------------------------------------------------------------------
# get_exception
# ---------------------------------------------------------------------------


async def test_get_exception_returns_dict_when_found(fake_pool):
    """get_exception 命中时返回 dict，analysis 反序列化。"""
    fake_pool.conn.fetchrow.return_value = FakeRecord(
        id=1,
        exception_id="exc-0001",
        source="instruction_timeout",
        instruction_id="instr-0001",
        description="超时",
        status="ANALYZED",
        analysis='{"root_cause": "device_busy", "action": "retry"}',
        created_at=_ts(0),
        updated_at=_ts(5),
    )

    result = await shared_db.get_exception("exc-0001")

    call = fake_pool.conn.fetchrow.call_args
    assert "WHERE exception_id = $1" in call.args[0]
    assert call.args[1] == "exc-0001"

    assert result["status"] == "ANALYZED"
    assert result["analysis"] == {"root_cause": "device_busy", "action": "retry"}


async def test_get_exception_returns_none_when_not_found(fake_pool):
    """get_exception 未命中时返回 None。"""
    fake_pool.conn.fetchrow.return_value = None

    result = await shared_db.get_exception("exc-missing")

    assert result is None


# ---------------------------------------------------------------------------
# list_exceptions
# ---------------------------------------------------------------------------


async def test_list_exceptions_no_filter(fake_pool):
    """无过滤时查询全部，按 created_at DESC。"""
    fake_pool.conn.fetchrow.return_value = FakeRecord(cnt=10)
    fake_pool.conn.fetch.return_value = [
        FakeRecord(
            id=i,
            exception_id=f"exc-{i:04d}",
            source="manual",
            instruction_id=None,
            description=f"desc-{i}",
            status="OPEN",
            analysis=None,
            created_at=_ts(i),
            updated_at=_ts(i),
        )
        for i in range(1, 4)
    ]

    result = await shared_db.list_exceptions(page=1, size=20)

    # COUNT 无 WHERE
    count_call = fake_pool.conn.fetchrow.call_args
    assert "WHERE" not in count_call.args[0]

    fetch_call = fake_pool.conn.fetch.call_args
    assert "ORDER BY created_at DESC" in fetch_call.args[0]
    assert "LIMIT $1 OFFSET $2" in fetch_call.args[0]
    assert fetch_call.args[1] == 20
    assert fetch_call.args[2] == 0

    assert result["total"] == 10
    assert len(result["records"]) == 3


async def test_list_exceptions_with_status_filter(fake_pool):
    """status 过滤时 WHERE 与占位符顺序正确。"""
    fake_pool.conn.fetchrow.return_value = FakeRecord(cnt=2)
    fake_pool.conn.fetch.return_value = []

    await shared_db.list_exceptions(page=1, size=5, status="OPEN")

    count_call = fake_pool.conn.fetchrow.call_args
    assert "WHERE status = $1" in count_call.args[0]
    assert count_call.args[1] == "OPEN"

    fetch_call = fake_pool.conn.fetch.call_args
    assert "WHERE status = $1" in fetch_call.args[0]
    assert "LIMIT $2 OFFSET $3" in fetch_call.args[0]
    assert fetch_call.args[1] == "OPEN"
    assert fetch_call.args[2] == 5
    assert fetch_call.args[3] == 0


async def test_list_exceptions_normalizes_invalid_page_size(fake_pool):
    """page<1 / size<1 归一。"""
    fake_pool.conn.fetchrow.return_value = FakeRecord(cnt=0)
    fake_pool.conn.fetch.return_value = []

    result = await shared_db.list_exceptions(page=-1, size=-5)

    assert result["page"] == 1
    assert result["size"] == 1


# ---------------------------------------------------------------------------
# update_exception_status
# ---------------------------------------------------------------------------


async def test_update_exception_status_with_analysis(fake_pool):
    """带 analysis 时应同时更新 status 与 analysis（jsonb cast）。"""
    fake_pool.conn.fetchrow.return_value = FakeRecord(
        id=1,
        exception_id="exc-0001",
        source="instruction_timeout",
        instruction_id="instr-0001",
        description="超时",
        status="ANALYZED",
        analysis='{"root_cause": "busy"}',
        created_at=_ts(0),
        updated_at=_ts(5),
    )

    result = await shared_db.update_exception_status(
        "exc-0001", "ANALYZED", analysis={"root_cause": "busy"}
    )

    call = fake_pool.conn.fetchrow.call_args
    sql = call.args[0]
    assert "UPDATE exception_records" in sql
    assert "SET status = $1, analysis = $2::jsonb" in sql
    assert "WHERE exception_id = $3" in sql
    assert "RETURNING" in sql
    args = call.args[1:]
    assert args[0] == "ANALYZED"
    assert '"root_cause": "busy"' in args[1]
    assert args[1] == '{"root_cause": "busy"}'
    assert args[2] == "exc-0001"

    assert result["status"] == "ANALYZED"
    assert result["analysis"] == {"root_cause": "busy"}


async def test_update_exception_status_without_analysis(fake_pool):
    """不带 analysis 时仅更新 status。"""
    fake_pool.conn.fetchrow.return_value = FakeRecord(
        id=1,
        exception_id="exc-0001",
        source="manual",
        instruction_id=None,
        description="desc",
        status="CLOSED",
        analysis=None,
        created_at=_ts(0),
        updated_at=_ts(10),
    )

    result = await shared_db.update_exception_status("exc-0001", "CLOSED")

    call = fake_pool.conn.fetchrow.call_args
    sql = call.args[0]
    assert "SET status = $1, updated_at = NOW()" in sql
    assert "analysis = $1::jsonb" not in sql  # SET 子句不更新 analysis
    assert "analysis = $2::jsonb" not in sql  # SET 子句不更新 analysis
    assert call.args[1] == "CLOSED"
    assert call.args[2] == "exc-0001"

    assert result["status"] == "CLOSED"
    assert result["analysis"] is None


async def test_update_exception_status_returns_none_when_not_found(fake_pool):
    """异常不存在时返回 None。"""
    fake_pool.conn.fetchrow.return_value = None

    result = await shared_db.update_exception_status("exc-missing", "CLOSED")

    assert result is None


# ---------------------------------------------------------------------------
# create_approval
# ---------------------------------------------------------------------------


async def test_create_approval_inserts_and_returns_dict(fake_pool):
    """create_approval 应 INSERT 并返回 dict。"""
    fake_pool.conn.fetchrow.return_value = FakeRecord(
        id=1,
        instruction_id="instr-0001",
        decision="approve",
        approver="user-001",
        comment="同意执行",
        created_at=_ts(0),
    )

    result = await shared_db.create_approval(
        instruction_id="instr-0001",
        decision="approve",
        approver="user-001",
        comment="同意执行",
    )

    call = fake_pool.conn.fetchrow.call_args
    sql = call.args[0]
    assert "INSERT INTO approvals" in sql
    assert "RETURNING" in sql
    args = call.args[1:]
    assert args[0] == "instr-0001"
    assert args[1] == "approve"
    assert args[2] == "user-001"
    assert args[3] == "同意执行"

    assert result["id"] == 1
    assert result["instruction_id"] == "instr-0001"
    assert result["decision"] == "approve"
    assert result["approver"] == "user-001"
    assert result["comment"] == "同意执行"
    assert result["created_at"] == _ts(0).isoformat()


async def test_create_approval_nullable_fields(fake_pool):
    """approver / comment 可为 None。"""
    fake_pool.conn.fetchrow.return_value = FakeRecord(
        id=2,
        instruction_id="instr-0002",
        decision="reject",
        approver=None,
        comment=None,
        created_at=_ts(0),
    )

    result = await shared_db.create_approval(
        "instr-0002", "reject", None, None
    )

    assert result["approver"] is None
    assert result["comment"] is None


# ---------------------------------------------------------------------------
# get_approvals_by_instruction
# ---------------------------------------------------------------------------


async def test_get_approvals_by_instruction_returns_list(fake_pool):
    """返回某指令的全部审批记录，按 created_at ASC。"""
    fake_pool.conn.fetch.return_value = [
        FakeRecord(
            id=1,
            instruction_id="instr-0001",
            decision="approve",
            approver="user-a",
            comment="ok",
            created_at=_ts(0),
        ),
        FakeRecord(
            id=2,
            instruction_id="instr-0001",
            decision="approve",
            approver="user-b",
            comment="同意",
            created_at=_ts(5),
        ),
    ]

    result = await shared_db.get_approvals_by_instruction("instr-0001")

    call = fake_pool.conn.fetch.call_args
    sql = call.args[0]
    assert "FROM approvals WHERE instruction_id = $1" in sql
    assert "ORDER BY created_at ASC" in sql
    assert call.args[1] == "instr-0001"

    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[0]["approver"] == "user-a"
    assert result[1]["id"] == 2
    assert result[1]["comment"] == "同意"


async def test_get_approvals_by_instruction_empty(fake_pool):
    """无审批记录时返回空列表。"""
    fake_pool.conn.fetch.return_value = []

    result = await shared_db.get_approvals_by_instruction("instr-none")

    assert result == []


# ---------------------------------------------------------------------------
# 行转 dict 辅助函数直接测试
# ---------------------------------------------------------------------------


def test_parse_jsonb_handles_str_dict_list_none():
    """parse_jsonb 应兼容 str / dict / list / None。"""
    assert shared_db.parse_jsonb(None) is None
    assert shared_db.parse_jsonb('{"k": 1}') == {"k": 1}
    assert shared_db.parse_jsonb({"k": 1}) == {"k": 1}
    assert shared_db.parse_jsonb([1, 2]) == [1, 2]
    # 其它类型回退 None
    assert shared_db.parse_jsonb(123) is None


def test_fmt_ts_handles_naive_and_aware_datetime():
    """fmt_ts 无时区时按 UTC 处理，有时区时直接 ISO。"""
    naive = datetime(2026, 7, 9, 10, 0, 0)
    aware = datetime(2026, 7, 9, 10, 0, 0, tzinfo=timezone.utc)

    naive_str = shared_db.fmt_ts(naive)
    assert naive_str == "2026-07-09T10:00:00+00:00"

    aware_str = shared_db.fmt_ts(aware)
    assert aware_str == "2026-07-09T10:00:00+00:00"

    assert shared_db.fmt_ts(None) == ""


def test_instruction_row_to_dict_maps_all_fields():
    """_instruction_row_to_dict 应映射全部字段。"""
    row = FakeRecord(
        id=1,
        instruction_id="instr-0001",
        source_workflow_id="wf-1",
        type="REPAIR",
        payload='{"a": 1}',
        status="PENDING",
        priority="HIGH",
        auto_execute=True,
        created_at=datetime(2026, 7, 9, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 9, 10, 5, 0, tzinfo=timezone.utc),
    )

    result = shared_db._instruction_row_to_dict(row)

    assert result == {
        "id": 1,
        "instruction_id": "instr-0001",
        "source_workflow_id": "wf-1",
        "type": "REPAIR",
        "payload": {"a": 1},
        "status": "PENDING",
        "priority": "HIGH",
        "auto_execute": True,
        "created_at": "2026-07-09T10:00:00+00:00",
        "updated_at": "2026-07-09T10:05:00+00:00",
    }


def test_exception_row_to_dict_maps_all_fields():
    """_exception_row_to_dict 应映射全部字段。"""
    row = FakeRecord(
        id=1,
        exception_id="exc-0001",
        source="manual",
        instruction_id="instr-0001",
        description="desc",
        status="CLOSED",
        analysis='{"root": "x"}',
        created_at=datetime(2026, 7, 9, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 9, 10, 5, 0, tzinfo=timezone.utc),
    )

    result = shared_db._exception_row_to_dict(row)

    assert result == {
        "id": 1,
        "exception_id": "exc-0001",
        "source": "manual",
        "instruction_id": "instr-0001",
        "description": "desc",
        "status": "CLOSED",
        "analysis": {"root": "x"},
        "created_at": "2026-07-09T10:00:00+00:00",
        "updated_at": "2026-07-09T10:05:00+00:00",
    }


def test_approval_row_to_dict_maps_all_fields():
    """_approval_row_to_dict 应映射全部字段。"""
    row = FakeRecord(
        id=1,
        instruction_id="instr-0001",
        decision="approve",
        approver="user-001",
        comment="ok",
        created_at=datetime(2026, 7, 9, 10, 0, 0, tzinfo=timezone.utc),
    )

    result = shared_db._approval_row_to_dict(row)

    assert result == {
        "id": 1,
        "instruction_id": "instr-0001",
        "decision": "approve",
        "approver": "user-001",
        "comment": "ok",
        "created_at": "2026-07-09T10:00:00+00:00",
    }
