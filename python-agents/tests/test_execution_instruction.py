"""instruction_service 业务逻辑单元测试。

不触达真实 PostgreSQL：通过 monkeypatch 替换 instruction_service.db 上的
CRUD 函数为 AsyncMock，验证：
1. 自动生成模式（diagnosis + schedule_adjustment → 2 条指令）；
2. 手动模式（type + payload → 1 条指令）；
3. _should_auto_execute 规则（REPAIR+MEDIUM 自动、PARAM_CHANGE 审批、CRITICAL 审批）；
4. list / get / 状态机合法与非法跳转。

遵循 test_execution_db.py / test_quality_api.py 风格。
"""

from unittest.mock import AsyncMock

import pytest

from agent_execution import instruction_service
from agent_execution.models import (
    InstructionCreateRequest,
    InstructionPriority,
    InstructionStatus,
    InstructionType,
    ProgressRequest,
)


# ---------------------------------------------------------------------------
# 公共辅助
# ---------------------------------------------------------------------------


def _fake_record(**overrides) -> dict:
    """构造一条 DB 返回的指令记录 dict（合并入参覆盖默认字段）。"""
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


@pytest.fixture
def mock_db(monkeypatch):
    """批量替换 instruction_service.db 上的 CRUD 函数为 AsyncMock。

    返回 dict 便于各用例按需配置 return_value / side_effect。
    """
    mocks = {
        "create_instruction": AsyncMock(),
        "get_instruction": AsyncMock(return_value=None),
        "list_instructions": AsyncMock(),
        "update_instruction_status": AsyncMock(),
    }
    for name, m in mocks.items():
        monkeypatch.setattr(instruction_service.db, name, m)
    return mocks


# ---------------------------------------------------------------------------
# create_instructions
# ---------------------------------------------------------------------------


async def test_create_instructions_auto_generate_two(mock_db):
    """自动生成模式：diagnosis + schedule_adjustment → 2 条指令（REPAIR + PRODUCTION_ADJUST）。"""
    created: list[dict] = []

    async def _fake_create(**kwargs):
        record = _fake_record(**kwargs)
        created.append(record)
        return record

    mock_db["create_instruction"].side_effect = _fake_create

    req = InstructionCreateRequest(
        source_workflow_id="wf-abc",
        diagnosis={"root_causes": ["head_wear"]},
        schedule_adjustment={"estimated_delay_hours": 1.0},
        priority=InstructionPriority.MEDIUM,
    )
    result = await instruction_service.create_instructions(req)

    # 2 条指令
    assert len(result) == 2
    assert len(created) == 2

    # 第一条 REPAIR，payload 含 diagnosis
    assert created[0]["type"] == "REPAIR"
    assert created[0]["payload"] == {"diagnosis": {"root_causes": ["head_wear"]}}
    # 第二条 PRODUCTION_ADJUST，payload 含 schedule_adjustment
    assert created[1]["type"] == "PRODUCTION_ADJUST"
    assert created[1]["payload"] == {
        "schedule_adjustment": {"estimated_delay_hours": 1.0}
    }

    # 都带 source_workflow_id 与 MEDIUM
    for rec in created:
        assert rec["source_workflow_id"] == "wf-abc"
        assert rec["priority"] == "MEDIUM"
        # instruction_id 前缀
        assert rec["instruction_id"].startswith("instr-")


async def test_create_instructions_auto_generate_diagnosis_only(mock_db):
    """仅 diagnosis → 1 条 REPAIR 指令。"""
    mock_db["create_instruction"].return_value = _fake_record()

    req = InstructionCreateRequest(
        source_workflow_id="wf-x",
        diagnosis={"root_causes": ["x"]},
    )
    result = await instruction_service.create_instructions(req)

    assert len(result) == 1
    call = mock_db["create_instruction"].call_args
    assert call.kwargs["type"] == "REPAIR"
    assert call.kwargs["payload"] == {"diagnosis": {"root_causes": ["x"]}}


async def test_create_instructions_manual_single(mock_db):
    """手动模式：type + payload → 1 条指令，source_workflow_id=None。"""
    mock_db["create_instruction"].return_value = _fake_record(
        type="PARAM_CHANGE", payload={"param": "speed"}
    )

    req = InstructionCreateRequest(
        type=InstructionType.PARAM_CHANGE,
        payload={"param": "speed"},
        priority=InstructionPriority.LOW,
    )
    result = await instruction_service.create_instructions(req)

    assert len(result) == 1
    call = mock_db["create_instruction"].call_args
    assert call.kwargs["type"] == "PARAM_CHANGE"
    assert call.kwargs["payload"] == {"param": "speed"}
    assert call.kwargs["source_workflow_id"] is None
    assert call.kwargs["priority"] == "LOW"


# ---------------------------------------------------------------------------
# _should_auto_execute 规则（通过 create_instructions 端到端验证）
# ---------------------------------------------------------------------------


async def test_auto_execute_repair_medium_is_approved(mock_db):
    """REPAIR + MEDIUM → auto_execute=True → status=APPROVED。"""
    mock_db["create_instruction"].return_value = _fake_record()

    req = InstructionCreateRequest(
        type=InstructionType.REPAIR,
        payload={"a": 1},
        priority=InstructionPriority.MEDIUM,
    )
    await instruction_service.create_instructions(req)

    call = mock_db["create_instruction"].call_args
    assert call.kwargs["auto_execute"] is True
    assert call.kwargs["status"] == "APPROVED"


async def test_auto_execute_repair_low_is_approved(mock_db):
    """REPAIR + LOW → auto_execute=True。"""
    mock_db["create_instruction"].return_value = _fake_record()

    req = InstructionCreateRequest(
        type=InstructionType.REPAIR,
        payload={"a": 1},
        priority=InstructionPriority.LOW,
    )
    await instruction_service.create_instructions(req)

    call = mock_db["create_instruction"].call_args
    assert call.kwargs["auto_execute"] is True
    assert call.kwargs["status"] == "APPROVED"


async def test_auto_execute_param_change_needs_approval(mock_db):
    """PARAM_CHANGE + MEDIUM → auto_execute=False → status=PENDING_APPROVAL。"""
    mock_db["create_instruction"].return_value = _fake_record()

    req = InstructionCreateRequest(
        type=InstructionType.PARAM_CHANGE,
        payload={"p": 1},
        priority=InstructionPriority.MEDIUM,
    )
    await instruction_service.create_instructions(req)

    call = mock_db["create_instruction"].call_args
    assert call.kwargs["auto_execute"] is False
    assert call.kwargs["status"] == "PENDING_APPROVAL"


async def test_auto_execute_critical_needs_approval(mock_db):
    """REPAIR + CRITICAL → auto_execute=False（priority 在需审批列表）。"""
    mock_db["create_instruction"].return_value = _fake_record()

    req = InstructionCreateRequest(
        type=InstructionType.REPAIR,
        payload={"a": 1},
        priority=InstructionPriority.CRITICAL,
    )
    await instruction_service.create_instructions(req)

    call = mock_db["create_instruction"].call_args
    assert call.kwargs["auto_execute"] is False
    assert call.kwargs["status"] == "PENDING_APPROVAL"


def test_should_auto_execute_rule_matrix():
    """直接验证 _should_auto_execute 全矩阵。"""
    # (type, priority) -> expected
    cases = [
        (InstructionType.REPAIR, InstructionPriority.LOW, True),
        (InstructionType.REPAIR, InstructionPriority.MEDIUM, True),
        (InstructionType.REPAIR, InstructionPriority.CRITICAL, False),
        (
            InstructionType.PRODUCTION_ADJUST,
            InstructionPriority.MEDIUM,
            True,
        ),
        (
            InstructionType.PARAM_CHANGE,
            InstructionPriority.MEDIUM,
            False,
        ),
        (InstructionType.PARAM_CHANGE, InstructionPriority.LOW, False),
        (InstructionType.PARAM_CHANGE, InstructionPriority.CRITICAL, False),
    ]
    for instr_type, priority, expected in cases:
        got = instruction_service._should_auto_execute(instr_type, priority)
        assert got is expected, (
            f"_should_auto_execute({instr_type}, {priority}) = {got}, "
            f"expected {expected}"
        )


# ---------------------------------------------------------------------------
# get / list
# ---------------------------------------------------------------------------


async def test_get_instruction_returns_dict(mock_db):
    """get 命中返回 dict。"""
    mock_db["get_instruction"].return_value = _fake_record(
        instruction_id="instr-1"
    )
    result = await instruction_service.get_instruction("instr-1")
    assert result["instruction_id"] == "instr-1"
    mock_db["get_instruction"].assert_awaited_once_with("instr-1")


async def test_get_instruction_returns_none(mock_db):
    """get 未命中返回 None。"""
    mock_db["get_instruction"].return_value = None
    result = await instruction_service.get_instruction("instr-missing")
    assert result is None


async def test_list_instructions_passes_filters(mock_db):
    """list 应透传 page/size/status/type 给 db.list_instructions。"""
    mock_db["list_instructions"].return_value = {
        "records": [],
        "total": 0,
        "page": 1,
        "size": 20,
    }
    result = await instruction_service.list_instructions(
        page=2, size=10, status="PENDING", type="REPAIR"
    )
    mock_db["list_instructions"].assert_awaited_once_with(
        2, 10, "PENDING", "REPAIR"
    )
    assert result["page"] == 1


# ---------------------------------------------------------------------------
# update_progress 状态机
# ---------------------------------------------------------------------------


async def test_update_progress_approved_to_executing(mock_db):
    """合法：APPROVED → EXECUTING。"""
    mock_db["get_instruction"].return_value = _fake_record(status="APPROVED")
    mock_db["update_instruction_status"].return_value = _fake_record(
        status="EXECUTING"
    )
    req = ProgressRequest(status=InstructionStatus.EXECUTING)
    result = await instruction_service.update_progress("instr-1", req)
    assert result["status"] == "EXECUTING"
    mock_db["update_instruction_status"].assert_awaited_once()
    call = mock_db["update_instruction_status"].call_args
    assert call.args[0] == "instr-1"
    assert call.args[1] == "EXECUTING"
    assert call.kwargs["note"] is None


async def test_update_progress_executing_to_completed(mock_db):
    """合法：EXECUTING → COMPLETED。"""
    mock_db["get_instruction"].return_value = _fake_record(status="EXECUTING")
    mock_db["update_instruction_status"].return_value = _fake_record(
        status="COMPLETED"
    )
    req = ProgressRequest(status=InstructionStatus.COMPLETED, note="done")
    result = await instruction_service.update_progress("instr-1", req)
    assert result["status"] == "COMPLETED"
    assert mock_db["update_instruction_status"].call_args.kwargs["note"] == "done"


async def test_update_progress_executing_to_failed(mock_db):
    """合法：EXECUTING → FAILED。"""
    mock_db["get_instruction"].return_value = _fake_record(status="EXECUTING")
    mock_db["update_instruction_status"].return_value = _fake_record(
        status="FAILED"
    )
    req = ProgressRequest(status=InstructionStatus.FAILED)
    result = await instruction_service.update_progress("instr-1", req)
    assert result["status"] == "FAILED"


async def test_update_progress_pending_to_approved(mock_db):
    """合法（罕见）：PENDING → APPROVED。"""
    mock_db["get_instruction"].return_value = _fake_record(status="PENDING")
    mock_db["update_instruction_status"].return_value = _fake_record(
        status="APPROVED"
    )
    req = ProgressRequest(status=InstructionStatus.APPROVED)
    result = await instruction_service.update_progress("instr-1", req)
    assert result["status"] == "APPROVED"


async def test_update_progress_invalid_transition_raises(mock_db):
    """非法：COMPLETED → EXECUTING 抛 ValueError。"""
    mock_db["get_instruction"].return_value = _fake_record(status="COMPLETED")
    req = ProgressRequest(status=InstructionStatus.EXECUTING)
    with pytest.raises(ValueError, match="非法状态跳转"):
        await instruction_service.update_progress("instr-1", req)
    # 非法跳转不应触发 update
    mock_db["update_instruction_status"].assert_not_awaited()


async def test_update_progress_pending_approval_to_approved_raises(mock_db):
    """PENDING_APPROVAL → APPROVED 不允许经 progress（仅审批接口）。"""
    mock_db["get_instruction"].return_value = _fake_record(
        status="PENDING_APPROVAL"
    )
    req = ProgressRequest(status=InstructionStatus.APPROVED)
    with pytest.raises(ValueError, match="非法状态跳转"):
        await instruction_service.update_progress("instr-1", req)


async def test_update_progress_not_found_raises(mock_db):
    """指令不存在 → ValueError。"""
    mock_db["get_instruction"].return_value = None
    req = ProgressRequest(status=InstructionStatus.EXECUTING)
    with pytest.raises(ValueError, match="指令不存在"):
        await instruction_service.update_progress("instr-missing", req)


async def test_update_progress_update_returns_none_raises(mock_db):
    """get 命中但 update 返回 None（竞态删除）→ ValueError。"""
    mock_db["get_instruction"].return_value = _fake_record(status="APPROVED")
    mock_db["update_instruction_status"].return_value = None
    req = ProgressRequest(status=InstructionStatus.EXECUTING)
    with pytest.raises(ValueError, match="指令不存在"):
        await instruction_service.update_progress("instr-1", req)
