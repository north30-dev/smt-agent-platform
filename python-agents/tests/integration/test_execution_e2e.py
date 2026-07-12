"""执行协同 Agent 端到端集成测试。

验证指令生命周期、异常生命周期、自动生成指令的完整链路。
需要 agent-execution + PostgreSQL 运行。

环境受限时（服务不可达）自动 skip。
"""

import os
import time

import httpx
import pytest

EXECUTION_BASE = os.getenv("E2E_EXECUTION_BASE", "http://localhost:8006")


def _service_available(url: str) -> bool:
    for path in ("/docs", "/actuator/health", "/healthz"):
        try:
            resp = httpx.get(f"{url}{path}", timeout=3.0)
            if resp.status_code < 500:
                return True
        except Exception:
            continue
    return False


@pytest.fixture(autouse=True)
def _skip_if_unavailable():
    if not _service_available(EXECUTION_BASE):
        pytest.skip("agent-execution 不可达")


@pytest.mark.integration
def test_instruction_lifecycle_e2e():
    """手动创建指令 → 查询 → 审批 → 更新进度 → 验证最终状态。"""
    # 创建指令（手动模式，CRITICAL 优先级需审批）
    create_resp = httpx.post(
        f"{EXECUTION_BASE}/v1/execution/instructions",
        json={
            "type": "REPAIR",
            "payload": {"device_id": 1, "action": "更换吸嘴"},
            "priority": "CRITICAL",
        },
        timeout=10.0,
    )
    assert create_resp.status_code == 200, f"指令创建失败: {create_resp.text}"
    instructions = create_resp.json()["instructions"]
    assert len(instructions) == 1
    instr = instructions[0]
    assert instr["status"] == "PENDING_APPROVAL"
    instr_id = instr["instruction_id"]

    # 查询单条指令
    get_resp = httpx.get(f"{EXECUTION_BASE}/v1/execution/instructions/{instr_id}", timeout=10.0)
    assert get_resp.status_code == 200
    assert get_resp.json()["instruction_id"] == instr_id

    # 审批（approve）
    approve_resp = httpx.post(
        f"{EXECUTION_BASE}/v1/execution/instructions/{instr_id}/approve",
        json={"decision": "APPROVE", "approver": "e2e-test"},
        timeout=10.0,
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "APPROVED"

    # 更新进度：EXECUTING
    exec_resp = httpx.post(
        f"{EXECUTION_BASE}/v1/execution/instructions/{instr_id}/progress",
        json={"status": "EXECUTING", "note": "开始执行"},
        timeout=10.0,
    )
    assert exec_resp.status_code == 200
    assert exec_resp.json()["status"] == "EXECUTING"

    # 更新进度：COMPLETED
    done_resp = httpx.post(
        f"{EXECUTION_BASE}/v1/execution/instructions/{instr_id}/progress",
        json={"status": "COMPLETED", "note": "执行完成"},
        timeout=10.0,
    )
    assert done_resp.status_code == 200
    assert done_resp.json()["status"] == "COMPLETED"

    # 查询指令列表，验证该指令存在
    list_resp = httpx.get(f"{EXECUTION_BASE}/v1/execution/instructions?size=5", timeout=10.0)
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert any(r["instruction_id"] == instr_id for r in data["records"])


@pytest.mark.integration
def test_exception_lifecycle_e2e():
    """创建异常记录 → 查询列表 → 验证通过 → 验证最终状态。"""
    # 创建异常
    create_resp = httpx.post(
        f"{EXECUTION_BASE}/v1/execution/exceptions",
        json={
            "source": "manual",
            "description": "E2E 测试：吸嘴堵塞导致抛料率升高",
        },
        timeout=10.0,
    )
    assert create_resp.status_code == 200, f"异常创建失败: {create_resp.text}"
    exc = create_resp.json()
    assert exc["status"] == "OPEN"
    exc_id = exc["exception_id"]

    # 查询异常列表
    list_resp = httpx.get(f"{EXECUTION_BASE}/v1/execution/exceptions?size=5", timeout=10.0)
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert any(r["exception_id"] == exc_id for r in data["records"])

    # 验证异常（通过 → CLOSED）
    verify_resp = httpx.post(
        f"{EXECUTION_BASE}/v1/execution/exceptions/{exc_id}/verify",
        json={"passed": True, "note": "已清理吸嘴"},
        timeout=10.0,
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["status"] == "CLOSED"


@pytest.mark.integration
def test_auto_instruction_from_workflow_e2e():
    """传入 source_workflow_id + diagnosis → 自动生成 REPAIR 指令。"""
    resp = httpx.post(
        f"{EXECUTION_BASE}/v1/execution/instructions",
        json={
            "source_workflow_id": "e2e-workflow-001",
            "diagnosis": {
                "root_cause": "吸嘴磨损",
                "solution": "更换吸嘴",
                "risk_level": "HIGH",
            },
            "priority": "MEDIUM",
        },
        timeout=10.0,
    )
    assert resp.status_code == 200, f"自动指令创建失败: {resp.text}"
    instructions = resp.json()["instructions"]
    assert len(instructions) >= 1
    instr = instructions[0]
    assert instr["type"] == "REPAIR"
    assert instr["source_workflow_id"] == "e2e-workflow-001"
    assert "diagnosis" in instr["payload"]
