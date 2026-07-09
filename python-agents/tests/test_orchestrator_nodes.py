"""agent_orchestrator.nodes 节点函数单元测试。

使用 monkeypatch 替换 nodes 模块内的 agent_clients 单例与 llm_client 模块，
不触达真实子 Agent 与大模型。

每个节点对 AgentUnavailable 做降级（写 errors + skipped），不向上抛出，
确保线性图能跑完所有节点。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_orchestrator.agent_clients import AgentUnavailable
from agent_orchestrator.nodes import (
    _merge_errors,
    maintenance_node,
    quality_node,
    scheduler_node,
    summary_node,
)
from shared.llm_client import LLMClientError


@pytest.fixture
def base_state():
    """构造节点测试用基础 state。"""
    return {
        "device_id": 1,
        "symptom": "贴片机异响",
        "diagnosis": None,
        "quality_assessment": None,
        "schedule_adjustment": None,
        "summary": None,
        "errors": {},
    }


# ---------------------------------------------------------------------------
# maintenance_node
# ---------------------------------------------------------------------------


async def test_maintenance_node_success(monkeypatch, base_state):
    """成功：返回 diagnosis 结果，不写 errors。"""
    mock_result = {
        "root_causes": ["轴承磨损"],
        "repair_suggestions": ["更换轴承"],
        "similar_cases": [],
    }
    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_maintenance",
        AsyncMock(return_value=mock_result),
    )

    result = await maintenance_node(base_state)

    assert result == {"diagnosis": mock_result}
    assert "errors" not in result


async def test_maintenance_node_unavailable(monkeypatch, base_state):
    """AgentUnavailable：返回 diagnosis=None 与 errors.maintenance。"""
    exc = AgentUnavailable("maintenance", "connection refused")
    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_maintenance",
        AsyncMock(side_effect=exc),
    )

    result = await maintenance_node(base_state)

    assert result["diagnosis"] is None
    assert result["errors"]["maintenance"] == "connection refused"


async def test_maintenance_node_merges_existing_errors(monkeypatch, base_state):
    """已有 errors 时，新错误应叠加而非覆盖。"""
    base_state["errors"] = {"other": "previous error"}
    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_maintenance",
        AsyncMock(side_effect=AgentUnavailable("maintenance", "down")),
    )

    result = await maintenance_node(base_state)

    assert result["errors"]["other"] == "previous error"
    assert result["errors"]["maintenance"] == "down"


# ---------------------------------------------------------------------------
# quality_node
# ---------------------------------------------------------------------------


async def test_quality_node_success(monkeypatch, base_state):
    """成功：返回 quality_assessment。"""
    mock_result = {
        "device_id": 1,
        "root_causes": ["焊膏偏移"],
        "corrective_actions": ["校准 SPI"],
        "similar_cases": [],
    }
    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_quality",
        AsyncMock(return_value=mock_result),
    )

    result = await quality_node(base_state)

    assert result == {"quality_assessment": mock_result}


async def test_quality_node_unavailable(monkeypatch, base_state):
    """AgentUnavailable：返回 skipped 状态与 errors.quality。"""
    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_quality",
        AsyncMock(side_effect=AgentUnavailable("quality", "timeout")),
    )

    result = await quality_node(base_state)

    assert result["quality_assessment"]["status"] == "skipped"
    assert "timeout" in result["quality_assessment"]["reason"]
    assert result["errors"]["quality"] == "timeout"


# ---------------------------------------------------------------------------
# scheduler_node
# ---------------------------------------------------------------------------


async def test_scheduler_node_success(monkeypatch, base_state):
    """成功：返回 schedule_adjustment，急单单号格式正确。"""
    mock_result = {
        "urgent_order_no": "URGENT-FAULT-1-1700000000",
        "affected_orders": ["ORD-001"],
        "estimated_delay_hours": 2.5,
        "adjustment_plan": {
            "changeover_suggestion": "切换至产品 B",
            "overtime_suggestion": "晚班加班 2 小时",
        },
    }
    captured = {}

    async def _fake_call_scheduler(order_no, product_model, quantity, delivery_date, source="user"):
        captured["order_no"] = order_no
        captured["product_model"] = product_model
        captured["quantity"] = quantity
        captured["delivery_date"] = delivery_date
        captured["source"] = source
        return mock_result

    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_scheduler",
        _fake_call_scheduler,
    )

    result = await scheduler_node(base_state)

    assert result == {"schedule_adjustment": mock_result}
    # 验证合成急单参数
    assert captured["order_no"].startswith("URGENT-FAULT-1-")
    assert captured["product_model"] == "UNKNOWN"
    assert captured["quantity"] == 1000
    # delivery_date 应为今天 +2 天的 ISO 日期
    from datetime import date, timedelta

    expected = (date.today() + timedelta(days=2)).isoformat()
    assert captured["delivery_date"] == expected
    # 合成急单 source 应标记为 orchestrator_synthetic
    assert captured["source"] == "orchestrator_synthetic"


async def test_scheduler_node_unavailable(monkeypatch, base_state):
    """AgentUnavailable：返回 skipped 与 errors.scheduler。"""
    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_scheduler",
        AsyncMock(side_effect=AgentUnavailable("scheduler", "refused")),
    )

    result = await scheduler_node(base_state)

    assert result["schedule_adjustment"]["status"] == "skipped"
    assert "refused" in result["schedule_adjustment"]["reason"]
    assert result["errors"]["scheduler"] == "refused"


# ---------------------------------------------------------------------------
# summary_node
# ---------------------------------------------------------------------------


async def test_summary_node_success(monkeypatch, base_state):
    """成功：调用 LLM 并返回 summary 文本。"""
    base_state["diagnosis"] = {"root_causes": ["x"]}
    base_state["quality_assessment"] = {"root_causes": ["y"]}
    base_state["schedule_adjustment"] = {"estimated_delay_hours": 1.0}

    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(return_value="设备异响风险较高，建议立即停机检修。")
    monkeypatch.setattr("agent_orchestrator.nodes.llm_client", mock_llm)

    result = await summary_node(base_state)

    assert result == {"summary": "设备异响风险较高，建议立即停机检修。"}
    mock_llm.chat.assert_called_once()
    # 验证 prompt 包含设备 ID 与故障现象
    user_msg = mock_llm.chat.call_args.args[0][1]["content"]
    assert "1" in user_msg
    assert "贴片机异响" in user_msg


async def test_summary_node_llm_error(monkeypatch, base_state):
    """LLMClientError：返回降级摘要，不写 errors。"""
    base_state["diagnosis"] = None
    base_state["quality_assessment"] = {"status": "skipped", "reason": "down"}
    base_state["schedule_adjustment"] = {"status": "skipped", "reason": "down"}

    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(side_effect=LLMClientError("llm timeout"))
    monkeypatch.setattr("agent_orchestrator.nodes.llm_client", mock_llm)

    result = await summary_node(base_state)

    assert result == {"summary": "摘要生成失败，详见各节点结果。"}
    assert "errors" not in result


async def test_summary_node_includes_skipped_info(monkeypatch, base_state):
    """降级节点信息应进入 prompt。"""
    base_state["diagnosis"] = None
    base_state["quality_assessment"] = {"status": "skipped", "reason": "quality down"}
    base_state["schedule_adjustment"] = {
        "status": "skipped",
        "reason": "scheduler down",
    }
    base_state["errors"] = {
        "maintenance": "maintenance down",
        "quality": "quality down",
    }

    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(return_value="summary")
    monkeypatch.setattr("agent_orchestrator.nodes.llm_client", mock_llm)

    await summary_node(base_state)

    user_msg = mock_llm.chat.call_args.args[0][1]["content"]
    assert "已跳过" in user_msg
    assert "quality down" in user_msg
    assert "scheduler down" in user_msg


# ---------------------------------------------------------------------------
# _merge_errors helper
# ---------------------------------------------------------------------------


def test_merge_errors_empty():
    """空 dict + 新 key → 仅含新 key。"""
    result = _merge_errors({}, "maintenance", "down")
    assert result == {"maintenance": "down"}


def test_merge_errors_accumulates():
    """已有 errors + 新 key → 累积。"""
    result = _merge_errors({"maintenance": "down"}, "quality", "timeout")
    assert result == {"maintenance": "down", "quality": "timeout"}


def test_merge_errors_overwrites_same_key():
    """同 key 写入应覆盖原值。"""
    result = _merge_errors({"maintenance": "old"}, "maintenance", "new")
    assert result == {"maintenance": "new"}


def test_merge_errors_does_not_mutate_input():
    """不应修改入参 dict。"""
    original = {"maintenance": "down"}
    _merge_errors(original, "quality", "timeout")
    assert original == {"maintenance": "down"}
