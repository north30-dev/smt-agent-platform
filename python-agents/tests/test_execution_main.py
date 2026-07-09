"""agent_execution.main FastAPI 接口集成测试。

使用 httpx.AsyncClient + ASGITransport(app=app) 调用真实路由，通过 monkeypatch
替换 instruction_service.db / exception_service.db / exception_service.llm_client
上的函数，不触达真实 PostgreSQL / LLM / Kafka。

ASGITransport 不触发 lifespan，因此 init_execution_tables / kafka 消费者均不启动，
测试仅覆盖路由 → 服务 → mock db 的链路。

覆盖：healthz、create instruction（自动生成 2 条）、list、404、非法状态跳转 400、
异常创建、异常验证、审批。
"""

from unittest.mock import AsyncMock

import httpx
import pytest

from agent_execution import exception_service, instruction_service, main as exec_main


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def client():
    """httpx.AsyncClient + ASGITransport，不触发 lifespan。

    raise_app_exceptions=False：允许 Exception 处理器返回 500 响应体而非重抛异常，
    对齐 test_orchestrator_api.py 的 raise_server_exceptions=False。
    """
    transport = httpx.ASGITransport(app=exec_main.app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as c:
        yield c


def _fake_instruction_record(**overrides) -> dict:
    base = {
        "id": 1,
        "instruction_id": "instr-fixture",
        "source_workflow_id": None,
        "type": "REPAIR",
        "payload": {"k": "v"},
        "status": "APPROVED",
        "priority": "MEDIUM",
        "auto_execute": True,
        "created_at": "2026-07-09T10:00:00+00:00",
        "updated_at": "2026-07-09T10:00:00+00:00",
    }
    base.update(overrides)
    return base


def _fake_exception_record(**overrides) -> dict:
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


# ---------------------------------------------------------------------------
# /healthz
# ---------------------------------------------------------------------------


async def test_healthz(client):
    """/healthz 应返回 200 与 healthy 状态。"""
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert isinstance(data["checks"], list)


# ---------------------------------------------------------------------------
# POST /v1/execution/instructions（自动生成）
# ---------------------------------------------------------------------------


async def test_create_instructions_auto_generate(client, monkeypatch):
    """自动生成模式：返回 2 条指令（REPAIR + PRODUCTION_ADJUST）。"""
    created: list[dict] = []

    async def _fake_create(**kwargs):
        rec = _fake_instruction_record(**kwargs)
        created.append(rec)
        return rec

    monkeypatch.setattr(
        instruction_service.db, "create_instruction", _fake_create
    )

    resp = await client.post(
        "/v1/execution/instructions",
        json={
            "source_workflow_id": "wf-abc",
            "diagnosis": {"root_causes": ["x"]},
            "schedule_adjustment": {"estimated_delay_hours": 1.0},
            "priority": "MEDIUM",
        },
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["instructions"]) == 2
    types = {i["type"] for i in data["instructions"]}
    assert types == {"REPAIR", "PRODUCTION_ADJUST"}
    # MEDIUM → auto_execute=True → APPROVED
    for i in data["instructions"]:
        assert i["auto_execute"] is True
        assert i["status"] == "APPROVED"
        assert i["source_workflow_id"] == "wf-abc"


async def test_create_instructions_manual_param_change_pending_approval(
    client, monkeypatch
):
    """手动模式 PARAM_CHANGE + MEDIUM → PENDING_APPROVAL。"""
    monkeypatch.setattr(
        instruction_service.db,
        "create_instruction",
        AsyncMock(
            return_value=_fake_instruction_record(
                type="PARAM_CHANGE",
                payload={"p": 1},
                status="PENDING_APPROVAL",
                auto_execute=False,
            )
        ),
    )

    resp = await client.post(
        "/v1/execution/instructions",
        json={
            "type": "PARAM_CHANGE",
            "payload": {"p": 1},
            "priority": "MEDIUM",
        },
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["instructions"]) == 1
    assert data["instructions"][0]["type"] == "PARAM_CHANGE"
    assert data["instructions"][0]["status"] == "PENDING_APPROVAL"


async def test_create_instructions_invalid_body_returns_422(client):
    """既无 source_workflow_id 也无 type+payload → 422。"""
    resp = await client.post(
        "/v1/execution/instructions",
        json={"priority": "MEDIUM"},
    )
    assert resp.status_code == 422


async def test_create_instructions_invalid_priority_returns_422(client):
    """非法 priority 值 → 422。"""
    resp = await client.post(
        "/v1/execution/instructions",
        json={"type": "REPAIR", "payload": {}, "priority": "URGENT"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /v1/execution/instructions（列表）
# ---------------------------------------------------------------------------


async def test_list_instructions(client, monkeypatch):
    """list 接口返回 InstructionListResponse 结构。"""
    monkeypatch.setattr(
        instruction_service.db,
        "list_instructions",
        AsyncMock(
            return_value={
                "records": [
                    _fake_instruction_record(
                        instruction_id="instr-1", status="PENDING"
                    )
                ],
                "total": 1,
                "page": 1,
                "size": 20,
            }
        ),
    )

    resp = await client.get("/v1/execution/instructions")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 1
    assert data["page"] == 1
    assert data["size"] == 20
    assert len(data["records"]) == 1
    assert data["records"][0]["instruction_id"] == "instr-1"


async def test_list_instructions_passes_query_params(client, monkeypatch):
    """list 接口应透传 page/size/status/type。"""
    list_mock = AsyncMock(
        return_value={"records": [], "total": 0, "page": 2, "size": 5}
    )
    monkeypatch.setattr(instruction_service.db, "list_instructions", list_mock)

    resp = await client.get(
        "/v1/execution/instructions?page=2&size=5&status=PENDING&type=REPAIR"
    )

    assert resp.status_code == 200
    list_mock.assert_awaited_once_with(2, 5, "PENDING", "REPAIR")


# ---------------------------------------------------------------------------
# GET /v1/execution/instructions/{id}
# ---------------------------------------------------------------------------


async def test_get_instruction_found(client, monkeypatch):
    """GET 已存在指令 → 200。"""
    monkeypatch.setattr(
        instruction_service.db,
        "get_instruction",
        AsyncMock(
            return_value=_fake_instruction_record(
                instruction_id="instr-1", status="COMPLETED"
            )
        ),
    )
    resp = await client.get("/v1/execution/instructions/instr-1")
    assert resp.status_code == 200
    assert resp.json()["instruction_id"] == "instr-1"
    assert resp.json()["status"] == "COMPLETED"


async def test_get_instruction_not_found_returns_404(client, monkeypatch):
    """GET 不存在指令 → 404 + ErrorResponse。"""
    monkeypatch.setattr(
        instruction_service.db,
        "get_instruction",
        AsyncMock(return_value=None),
    )
    resp = await client.get("/v1/execution/instructions/instr-missing")
    assert resp.status_code == 404
    data = resp.json()
    assert data["error"] == "instruction_not_found"
    assert "instr-missing" in data["message"]


# ---------------------------------------------------------------------------
# POST /v1/execution/instructions/{id}/progress（状态机）
# ---------------------------------------------------------------------------


async def test_progress_valid_transition(client, monkeypatch):
    """APPROVED → EXECUTING 合法跳转 → 200。"""
    monkeypatch.setattr(
        instruction_service.db,
        "get_instruction",
        AsyncMock(return_value=_fake_instruction_record(status="APPROVED")),
    )
    monkeypatch.setattr(
        instruction_service.db,
        "update_instruction_status",
        AsyncMock(
            return_value=_fake_instruction_record(
                instruction_id="instr-1", status="EXECUTING"
            )
        ),
    )
    resp = await client.post(
        "/v1/execution/instructions/instr-1/progress",
        json={"status": "EXECUTING", "note": "started"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "EXECUTING"


async def test_progress_invalid_transition_returns_400(client, monkeypatch):
    """COMPLETED → EXECUTING 非法跳转 → 400。"""
    monkeypatch.setattr(
        instruction_service.db,
        "get_instruction",
        AsyncMock(return_value=_fake_instruction_record(status="COMPLETED")),
    )
    resp = await client.post(
        "/v1/execution/instructions/instr-1/progress",
        json={"status": "EXECUTING"},
    )
    assert resp.status_code == 400
    data = resp.json()
    assert data["error"] == "invalid_param"
    assert "非法状态跳转" in data["message"]


async def test_progress_not_found_returns_400(client, monkeypatch):
    """progress 指令不存在 → 400（ValueError）。"""
    monkeypatch.setattr(
        instruction_service.db,
        "get_instruction",
        AsyncMock(return_value=None),
    )
    resp = await client.post(
        "/v1/execution/instructions/instr-missing/progress",
        json={"status": "EXECUTING"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "invalid_param"


# ---------------------------------------------------------------------------
# POST /v1/execution/instructions/{id}/approve
# ---------------------------------------------------------------------------


async def test_approve_route_approve(client, monkeypatch):
    """approve 路由：PENDING_APPROVAL → APPROVED。"""
    monkeypatch.setattr(
        instruction_service.db,
        "get_instruction",
        AsyncMock(return_value=_fake_instruction_record(status="PENDING_APPROVAL")),
    )
    monkeypatch.setattr(
        instruction_service.db,
        "update_instruction_status",
        AsyncMock(
            return_value=_fake_instruction_record(
                instruction_id="instr-1", status="APPROVED"
            )
        ),
    )
    monkeypatch.setattr(
        instruction_service.db,
        "create_approval",
        AsyncMock(
            return_value={
                "id": 1,
                "instruction_id": "instr-1",
                "decision": "approve",
                "approver": "system",
                "comment": None,
                "created_at": "2026-07-09T10:00:00+00:00",
            }
        ),
    )
    resp = await client.post(
        "/v1/execution/instructions/instr-1/approve",
        json={"decision": "approve", "approver": "system"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "APPROVED"


async def test_approve_route_not_pending_returns_400(client, monkeypatch):
    """approve 已 APPROVED 指令 → 400。"""
    monkeypatch.setattr(
        instruction_service.db,
        "get_instruction",
        AsyncMock(return_value=_fake_instruction_record(status="APPROVED")),
    )
    resp = await client.post(
        "/v1/execution/instructions/instr-1/approve",
        json={"decision": "approve"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "invalid_param"


# ---------------------------------------------------------------------------
# POST /v1/execution/exceptions
# ---------------------------------------------------------------------------


async def test_create_exception_route(client, monkeypatch):
    """创建异常记录 → 200。"""
    monkeypatch.setattr(
        exception_service.db,
        "create_exception",
        AsyncMock(
            return_value=_fake_exception_record(
                exception_id="exc-1", source="manual"
            )
        ),
    )
    resp = await client.post(
        "/v1/execution/exceptions",
        json={"source": "manual", "description": "超时"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["exception_id"] == "exc-1"
    assert data["source"] == "manual"


async def test_list_exceptions_route(client, monkeypatch):
    """list 异常 → 200。"""
    monkeypatch.setattr(
        exception_service.db,
        "list_exceptions",
        AsyncMock(
            return_value={
                "records": [
                    _fake_exception_record(exception_id="exc-1", status="OPEN")
                ],
                "total": 1,
                "page": 1,
                "size": 20,
            }
        ),
    )
    resp = await client.get("/v1/execution/exceptions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["records"][0]["exception_id"] == "exc-1"


async def test_verify_exception_pass(client, monkeypatch):
    """verify pass → CLOSED。"""
    monkeypatch.setattr(
        exception_service.db,
        "get_exception",
        AsyncMock(return_value=_fake_exception_record(status="ANALYZED")),
    )
    monkeypatch.setattr(
        exception_service.db,
        "update_exception_status",
        AsyncMock(
            return_value=_fake_exception_record(
                exception_id="exc-1", status="CLOSED"
            )
        ),
    )
    resp = await client.post(
        "/v1/execution/exceptions/exc-1/verify",
        json={"passed": True, "note": "ok"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["exception_id"] == "exc-1"
    assert data["status"] == "CLOSED"
    assert data["note"] == "ok"


async def test_verify_exception_not_found_returns_400(client, monkeypatch):
    """verify 不存在异常 → 400。"""
    monkeypatch.setattr(
        exception_service.db,
        "get_exception",
        AsyncMock(return_value=None),
    )
    resp = await client.post(
        "/v1/execution/exceptions/exc-missing/verify",
        json={"passed": True},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 兜底异常
# ---------------------------------------------------------------------------


async def test_create_exception_internal_error_returns_500(client, monkeypatch):
    """db.create_exception 抛未预期异常 → 500 + ErrorResponse。"""
    monkeypatch.setattr(
        exception_service.db,
        "create_exception",
        AsyncMock(side_effect=RuntimeError("db down")),
    )
    resp = await client.post(
        "/v1/execution/exceptions",
        json={"source": "manual", "description": "x"},
    )
    assert resp.status_code == 500
    assert resp.json()["error"] == "internal_error"
