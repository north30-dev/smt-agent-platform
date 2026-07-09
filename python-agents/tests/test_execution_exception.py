"""exception_service 业务逻辑单元测试。

不触达真实 PostgreSQL 与 LLM：通过 monkeypatch 替换 exception_service.db
与 exception_service.llm_client.chat，验证：
1. create_exception 生成 exc- 前缀 ID 并写入；
2. analyze 成功（LLM 返回 JSON）与降级（LLMClientError）；
3. verify pass/fail 状态切换；
4. list 透传参数。

遵循 test_execution_db.py / test_quality_api.py 风格。
"""

from unittest.mock import AsyncMock

import pytest

from agent_execution import exception_service
from agent_execution.models import (
    ExceptionCreateRequest,
    VerifyRequest,
)
from shared.llm_client import LLMClientError


def _fake_exception_record(**overrides) -> dict:
    """构造一条 DB 返回的异常记录 dict。"""
    base = {
        "id": 1,
        "exception_id": "exc-fixture",
        "source": "manual",
        "instruction_id": None,
        "description": "desc",
        "status": "OPEN",
        "analysis": None,
        "created_at": "2026-07-09T10:00:00+00:00",
        "updated_at": "2026-07-09T10:00:00+00:00",
    }
    base.update(overrides)
    return base


@pytest.fixture
def mock_db(monkeypatch):
    """批量替换 exception_service.db CRUD 函数为 AsyncMock。"""
    mocks = {
        "create_exception": AsyncMock(),
        "get_exception": AsyncMock(return_value=None),
        "list_exceptions": AsyncMock(),
        "update_exception_status": AsyncMock(),
    }
    for name, m in mocks.items():
        monkeypatch.setattr(exception_service.db, name, m)
    return mocks


@pytest.fixture
def mock_chat(monkeypatch):
    """替换 exception_service.llm_client.chat 为 AsyncMock。"""
    chat = AsyncMock(return_value='{"root_cause": "x", "action": "y"}')
    monkeypatch.setattr(exception_service.llm_client, "chat", chat)
    return chat


# ---------------------------------------------------------------------------
# create_exception
# ---------------------------------------------------------------------------


async def test_create_exception_generates_id(mock_db):
    """create_exception 生成 exc- 前缀 ID 并写入 DB。"""
    mock_db["create_exception"].return_value = _fake_exception_record(
        exception_id="exc-abc123",
    )
    req = ExceptionCreateRequest(
        source="manual",
        instruction_id="instr-1",
        description="超时",
    )
    result = await exception_service.create_exception(req)

    call = mock_db["create_exception"].call_args
    assert call.kwargs["exception_id"].startswith("exc-")
    assert call.kwargs["source"] == "manual"
    assert call.kwargs["instruction_id"] == "instr-1"
    assert call.kwargs["description"] == "超时"
    assert result["exception_id"] == "exc-abc123"


async def test_create_exception_null_instruction_id(mock_db):
    """instruction_id 可为 None。"""
    mock_db["create_exception"].return_value = _fake_exception_record(
        instruction_id=None
    )
    req = ExceptionCreateRequest(source="kafka_event", description="x")
    await exception_service.create_exception(req)
    assert mock_db["create_exception"].call_args.kwargs["instruction_id"] is None


# ---------------------------------------------------------------------------
# analyze_exception
# ---------------------------------------------------------------------------


async def test_analyze_success_parses_json(mock_db, mock_chat):
    """LLM 返回纯 JSON → 解析为 dict 写入 analysis，status=ANALYZED。"""
    mock_db["get_exception"].return_value = _fake_exception_record(
        exception_id="exc-1", description="超时"
    )
    mock_db["update_exception_status"].return_value = _fake_exception_record(
        exception_id="exc-1", status="ANALYZED",
        analysis={"root_cause": "x", "action": "y"},
    )

    result = await exception_service.analyze_exception("exc-1")

    mock_chat.assert_awaited_once()
    # messages 是 list[dict]
    messages = mock_chat.call_args.args[0]
    assert isinstance(messages, list)
    assert any("异常根因分析" in m["content"] for m in messages if m["role"] == "system")

    update_call = mock_db["update_exception_status"].call_args
    assert update_call.args[0] == "exc-1"
    assert update_call.args[1] == "ANALYZED"
    assert update_call.kwargs["analysis"] == {"root_cause": "x", "action": "y"}
    assert result["status"] == "ANALYZED"
    assert result["analysis"] == {"root_cause": "x", "action": "y"}


async def test_analyze_non_json_response_wraps(mock_db, mock_chat):
    """LLM 返回非 JSON 文本 → 包装为 manual_review。"""
    mock_chat.return_value = "这是纯文本根因描述"
    mock_db["get_exception"].return_value = _fake_exception_record(exception_id="exc-2")
    mock_db["update_exception_status"].return_value = _fake_exception_record(
        exception_id="exc-2", status="ANALYZED",
        analysis={"root_cause": "这是纯文本根因描述", "action": "manual_review"},
    )

    await exception_service.analyze_exception("exc-2")

    update_call = mock_db["update_exception_status"].call_args
    assert update_call.kwargs["analysis"] == {
        "root_cause": "这是纯文本根因描述",
        "action": "manual_review",
    }


async def test_analyze_llm_error_degraded(mock_db, mock_chat):
    """LLMClientError → 降级 analysis（status=degraded），仍推进到 ANALYZED。"""
    mock_chat.side_effect = LLMClientError("LLM timeout")
    mock_db["get_exception"].return_value = _fake_exception_record(exception_id="exc-3")
    mock_db["update_exception_status"].return_value = _fake_exception_record(
        exception_id="exc-3", status="ANALYZED",
        analysis={"status": "degraded", "message": "LLM 不可用，降级分析: LLM timeout"},
    )

    result = await exception_service.analyze_exception("exc-3")

    update_call = mock_db["update_exception_status"].call_args
    assert update_call.args[1] == "ANALYZED"
    assert update_call.kwargs["analysis"]["status"] == "degraded"
    assert "LLM timeout" in update_call.kwargs["analysis"]["message"]
    assert result["status"] == "ANALYZED"


async def test_analyze_not_found_raises(mock_db, mock_chat):
    """异常不存在 → ValueError。"""
    mock_db["get_exception"].return_value = None
    with pytest.raises(ValueError, match="异常不存在"):
        await exception_service.analyze_exception("exc-missing")
    mock_chat.assert_not_awaited()


# ---------------------------------------------------------------------------
# verify_exception
# ---------------------------------------------------------------------------


async def test_verify_passed_closes(mock_db):
    """passed=True → status=CLOSED。"""
    mock_db["get_exception"].return_value = _fake_exception_record(
        exception_id="exc-1", status="ANALYZED"
    )
    mock_db["update_exception_status"].return_value = _fake_exception_record(
        exception_id="exc-1", status="CLOSED"
    )
    req = VerifyRequest(passed=True, note="ok")
    result = await exception_service.verify_exception("exc-1", req)

    mock_db["update_exception_status"].assert_awaited_once_with("exc-1", "CLOSED")
    assert result["status"] == "CLOSED"


async def test_verify_failed_reopens(mock_db):
    """passed=False → status=OPEN（回退）。"""
    mock_db["get_exception"].return_value = _fake_exception_record(
        exception_id="exc-2", status="ANALYZED"
    )
    mock_db["update_exception_status"].return_value = _fake_exception_record(
        exception_id="exc-2", status="OPEN"
    )
    req = VerifyRequest(passed=False)
    result = await exception_service.verify_exception("exc-2", req)

    mock_db["update_exception_status"].assert_awaited_once_with("exc-2", "OPEN")
    assert result["status"] == "OPEN"


async def test_verify_not_found_raises(mock_db):
    """异常不存在 → ValueError。"""
    mock_db["get_exception"].return_value = None
    req = VerifyRequest(passed=True)
    with pytest.raises(ValueError, match="异常不存在"):
        await exception_service.verify_exception("exc-missing", req)


# ---------------------------------------------------------------------------
# list_exceptions
# ---------------------------------------------------------------------------


async def test_list_exceptions_passes_args(mock_db):
    """list 应透传 page/size/status。"""
    mock_db["list_exceptions"].return_value = {
        "records": [],
        "total": 0,
        "page": 2,
        "size": 5,
    }
    result = await exception_service.list_exceptions(
        page=2, size=5, status="OPEN"
    )
    mock_db["list_exceptions"].assert_awaited_once_with(2, 5, "OPEN")
    assert result["page"] == 2
    assert result["size"] == 5
