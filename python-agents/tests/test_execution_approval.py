"""approval_service 业务逻辑单元测试。

不触达真实 PostgreSQL：通过 monkeypatch 替换 approval_service.db 上的
get_instruction / update_instruction_status / create_approval，验证：
1. approve（PENDING_APPROVAL → APPROVED）+ 写审批记录；
2. reject（PENDING_APPROVAL → REJECTED）；
3. PENDING 状态也可审批；
4. 双重审批（已 APPROVED）→ ValueError；
5. 审批非待审批状态（如 COMPLETED/EXECUTING）→ ValueError；
6. 指令不存在 → ValueError。

遵循 test_execution_db.py / test_quality_api.py 风格。
"""

from unittest.mock import AsyncMock

import pytest

from agent_execution import approval_service
from agent_execution.models import ApprovalDecision, ApprovalRequest


def _fake_instruction(**overrides) -> dict:
    base = {
        "id": 1,
        "instruction_id": "instr-fixture",
        "source_workflow_id": None,
        "type": "REPAIR",
        "payload": {},
        "status": "PENDING_APPROVAL",
        "priority": "MEDIUM",
        "auto_execute": False,
        "created_at": "2026-07-09T10:00:00+00:00",
        "updated_at": "2026-07-09T10:00:00+00:00",
    }
    base.update(overrides)
    return base


def _fake_approval(**overrides) -> dict:
    base = {
        "id": 1,
        "instruction_id": "instr-fixture",
        "decision": "approve",
        "approver": "system",
        "comment": None,
        "created_at": "2026-07-09T10:00:00+00:00",
    }
    base.update(overrides)
    return base


@pytest.fixture
def mock_db(monkeypatch):
    mocks = {
        "get_instruction": AsyncMock(return_value=None),
        "update_instruction_status": AsyncMock(),
        "create_approval": AsyncMock(),
    }
    for name, m in mocks.items():
        monkeypatch.setattr(approval_service.db, name, m)
    return mocks


# ---------------------------------------------------------------------------
# approve / reject 成功路径
# ---------------------------------------------------------------------------


async def test_approve_pending_approval_to_approved(mock_db):
    """approve：PENDING_APPROVAL → APPROVED，并写 approvals 记录。"""
    mock_db["get_instruction"].return_value = _fake_instruction(
        status="PENDING_APPROVAL"
    )
    mock_db["update_instruction_status"].return_value = _fake_instruction(
        status="APPROVED"
    )
    mock_db["create_approval"].return_value = _fake_approval(decision="approve")

    req = ApprovalRequest(
        decision=ApprovalDecision.approve,
        approver="user-001",
        comment="同意执行",
    )
    result = await approval_service.approve("instr-1", req)

    assert result["status"] == "APPROVED"
    # update_status 调用
    mock_db["update_instruction_status"].assert_awaited_once_with(
        "instr-1", "APPROVED"
    )
    # create_approval 调用
    mock_db["create_approval"].assert_awaited_once()
    call = mock_db["create_approval"].call_args
    assert call.kwargs["instruction_id"] == "instr-1"
    assert call.kwargs["decision"] == "approve"
    assert call.kwargs["approver"] == "user-001"
    assert call.kwargs["comment"] == "同意执行"


async def test_reject_pending_approval_to_rejected(mock_db):
    """reject：PENDING_APPROVAL → REJECTED，写 reject 审批记录。"""
    mock_db["get_instruction"].return_value = _fake_instruction(
        status="PENDING_APPROVAL"
    )
    mock_db["update_instruction_status"].return_value = _fake_instruction(
        status="REJECTED"
    )
    mock_db["create_approval"].return_value = _fake_approval(decision="reject")

    req = ApprovalRequest(
        decision=ApprovalDecision.reject,
        approver="user-002",
        comment="风险过高",
    )
    result = await approval_service.approve("instr-1", req)

    assert result["status"] == "REJECTED"
    mock_db["update_instruction_status"].assert_awaited_once_with(
        "instr-1", "REJECTED"
    )
    assert mock_db["create_approval"].call_args.kwargs["decision"] == "reject"


async def test_approve_pending_status(mock_db):
    """PENDING 状态也可审批（仅 PENDING_APPROVAL / PENDING 可审批）。"""
    mock_db["get_instruction"].return_value = _fake_instruction(status="PENDING")
    mock_db["update_instruction_status"].return_value = _fake_instruction(
        status="APPROVED"
    )
    mock_db["create_approval"].return_value = _fake_approval()

    req = ApprovalRequest(decision=ApprovalDecision.approve)
    result = await approval_service.approve("instr-1", req)
    assert result["status"] == "APPROVED"


async def test_approve_default_approver(mock_db):
    """未传 approver 时默认 system。"""
    mock_db["get_instruction"].return_value = _fake_instruction(
        status="PENDING_APPROVAL"
    )
    mock_db["update_instruction_status"].return_value = _fake_instruction(
        status="APPROVED"
    )
    mock_db["create_approval"].return_value = _fake_approval(approver="system")

    req = ApprovalRequest(decision=ApprovalDecision.approve)
    await approval_service.approve("instr-1", req)

    assert mock_db["create_approval"].call_args.kwargs["approver"] == "system"


# ---------------------------------------------------------------------------
# 非法状态
# ---------------------------------------------------------------------------


async def test_approve_already_approved_raises(mock_db):
    """双重审批：已 APPROVED → ValueError（指令不在待审批状态）。"""
    mock_db["get_instruction"].return_value = _fake_instruction(status="APPROVED")
    req = ApprovalRequest(decision=ApprovalDecision.approve)
    with pytest.raises(ValueError, match="指令不在待审批状态"):
        await approval_service.approve("instr-1", req)
    # 不应触发 update / create_approval
    mock_db["update_instruction_status"].assert_not_awaited()
    mock_db["create_approval"].assert_not_awaited()


async def test_approve_completed_raises(mock_db):
    """COMPLETED 状态不可审批 → ValueError。"""
    mock_db["get_instruction"].return_value = _fake_instruction(status="COMPLETED")
    req = ApprovalRequest(decision=ApprovalDecision.approve)
    with pytest.raises(ValueError, match="指令不在待审批状态"):
        await approval_service.approve("instr-1", req)


async def test_approve_executing_raises(mock_db):
    """EXECUTING 状态不可审批 → ValueError。"""
    mock_db["get_instruction"].return_value = _fake_instruction(status="EXECUTING")
    req = ApprovalRequest(decision=ApprovalDecision.reject)
    with pytest.raises(ValueError, match="指令不在待审批状态"):
        await approval_service.approve("instr-1", req)


async def test_approve_rejected_raises(mock_db):
    """已 REJECTED 不可再审批 → ValueError。"""
    mock_db["get_instruction"].return_value = _fake_instruction(status="REJECTED")
    req = ApprovalRequest(decision=ApprovalDecision.approve)
    with pytest.raises(ValueError, match="指令不在待审批状态"):
        await approval_service.approve("instr-1", req)


# ---------------------------------------------------------------------------
# 不存在
# ---------------------------------------------------------------------------


async def test_approve_not_found_raises(mock_db):
    """指令不存在 → ValueError。"""
    mock_db["get_instruction"].return_value = None
    req = ApprovalRequest(decision=ApprovalDecision.approve)
    with pytest.raises(ValueError, match="指令不存在"):
        await approval_service.approve("instr-missing", req)
    mock_db["update_instruction_status"].assert_not_awaited()
    mock_db["create_approval"].assert_not_awaited()


async def test_approve_update_returns_none_raises(mock_db):
    """get 命中但 update 返回 None（竞态删除）→ ValueError，不写审批记录。"""
    mock_db["get_instruction"].return_value = _fake_instruction(
        status="PENDING_APPROVAL"
    )
    mock_db["update_instruction_status"].return_value = None
    req = ApprovalRequest(decision=ApprovalDecision.approve)
    with pytest.raises(ValueError, match="指令不存在"):
        await approval_service.approve("instr-1", req)
    mock_db["create_approval"].assert_not_awaited()
