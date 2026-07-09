"""agent_orchestrator.graph 端到端图执行测试。

验证线性图 maintenance → quality → scheduler → execution → summary 的执行顺序、
状态累积、以及"部分失败仍跑完所有节点"的降级语义。

通过 monkeypatch 替换 nodes 模块内 agent_clients 与 llm_client，
不触达真实 HTTP 服务与大模型。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_orchestrator.agent_clients import AgentUnavailable
from agent_orchestrator.graph import app_graph
from shared.llm_client import LLMClientError


def _initial_state():
    """构造图的初始输入 state。"""
    return {
        "device_id": 7,
        "symptom": "回流焊温度异常",
        "diagnosis": None,
        "quality_assessment": None,
        "schedule_adjustment": None,
        "instructions": [],
        "summary": None,
        "errors": {},
    }


def _patch_all_success(
    monkeypatch,
    diagnosis=None,
    quality=None,
    schedule=None,
    instructions=None,
    summary_text="LLM 汇总摘要",
):
    """统一 mock 四个子 Agent 调用与 LLM chat 全部成功。"""
    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_maintenance",
        AsyncMock(
            return_value=diagnosis
            or {"root_causes": ["x"], "repair_suggestions": ["y"], "similar_cases": []}
        ),
    )
    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_quality",
        AsyncMock(
            return_value=quality
            or {
                "device_id": 7,
                "root_causes": ["z"],
                "corrective_actions": ["w"],
                "similar_cases": [],
            }
        ),
    )
    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_scheduler",
        AsyncMock(
            return_value=schedule
            or {
                "urgent_order_no": "URGENT-FAULT-7-1",
                "affected_orders": [],
                "estimated_delay_hours": 0.0,
                "adjustment_plan": {
                    "changeover_suggestion": "n/a",
                    "overtime_suggestion": "n/a",
                },
            }
        ),
    )
    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_execution",
        AsyncMock(
            return_value=instructions
            or [
                {
                    "instruction_id": "INST-1",
                    "type": "REPAIR",
                    "payload": {"action": "更换轴承"},
                    "priority": "MEDIUM",
                }
            ]
        ),
    )
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(return_value=summary_text)
    monkeypatch.setattr("agent_orchestrator.nodes.llm_client", mock_llm)


# ---------------------------------------------------------------------------
# 全成功场景
# ---------------------------------------------------------------------------


async def test_graph_all_success(monkeypatch):
    """五节点全部成功：errors 为空，instructions 与 summary 文本就绪。"""
    _patch_all_success(monkeypatch, summary_text="一切正常")

    result = await app_graph.ainvoke(_initial_state())

    assert result["diagnosis"] is not None
    assert result["quality_assessment"] is not None
    assert result["schedule_adjustment"] is not None
    assert result["instructions"]  # 非空指令列表
    assert isinstance(result["instructions"], list)
    assert result["instructions"][0]["instruction_id"] == "INST-1"
    assert result["summary"] == "一切正常"
    assert result["errors"] == {}
    # 验证 device_id / symptom 透传
    assert result["device_id"] == 7
    assert result["symptom"] == "回流焊温度异常"


async def test_graph_state_accumulates_in_order(monkeypatch):
    """状态应在线性图中按节点顺序累积：每节点看到上一节点的最新写入。"""
    call_order = []

    async def _track_maintenance(device_id, symptom):
        call_order.append("maintenance")
        return {"root_causes": ["m"]}

    async def _track_quality(device_id, defect_description):
        call_order.append("quality")
        return {"root_causes": ["q"]}

    async def _track_scheduler(order_no, product_model, quantity, delivery_date, source="user"):
        call_order.append("scheduler")
        return {"urgent_order_no": order_no}

    async def _track_execution(source_workflow_id, diagnosis, schedule_adjustment):
        call_order.append("execution")
        return [{"instruction_id": "INST-1", "type": "REPAIR"}]

    async def _track_chat(messages, temperature=0.3):
        call_order.append("summary")
        return "summary"

    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_maintenance",
        _track_maintenance,
    )
    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_quality",
        _track_quality,
    )
    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_scheduler",
        _track_scheduler,
    )
    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_execution",
        _track_execution,
    )
    mock_llm = MagicMock()
    mock_llm.chat = _track_chat
    monkeypatch.setattr("agent_orchestrator.nodes.llm_client", mock_llm)

    await app_graph.ainvoke(_initial_state())

    # execution 应在 scheduler 之后、summary 之前执行
    assert call_order == ["maintenance", "quality", "scheduler", "execution", "summary"]


async def test_graph_execution_runs_after_scheduler_and_writes_instructions(monkeypatch):
    """execution_node 在 scheduler 之后运行，并将指令写入 final state。"""
    call_order = []
    captured_args = {}

    async def _track_scheduler(order_no, product_model, quantity, delivery_date, source="user"):
        call_order.append("scheduler")
        return {"urgent_order_no": order_no, "estimated_delay_hours": 1.0}

    async def _track_execution(source_workflow_id, diagnosis, schedule_adjustment):
        call_order.append("execution")
        captured_args["source_workflow_id"] = source_workflow_id
        captured_args["diagnosis"] = diagnosis
        captured_args["schedule_adjustment"] = schedule_adjustment
        return [
            {"instruction_id": "INST-A", "type": "REPAIR", "priority": "HIGH"},
            {"instruction_id": "INST-B", "type": "PRODUCTION_ADJUST", "priority": "LOW"},
        ]

    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_maintenance",
        AsyncMock(return_value={"root_causes": ["m"]}),
    )
    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_quality",
        AsyncMock(return_value={"root_causes": ["q"]}),
    )
    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_scheduler",
        _track_scheduler,
    )
    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_execution",
        _track_execution,
    )
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(return_value="summary")
    monkeypatch.setattr("agent_orchestrator.nodes.llm_client", mock_llm)

    result = await app_graph.ainvoke(_initial_state())

    # execution 在 scheduler 之后
    assert call_order == ["scheduler", "execution"]
    # instructions 写入 final state
    assert len(result["instructions"]) == 2
    assert result["instructions"][0]["instruction_id"] == "INST-A"
    assert result["instructions"][1]["instruction_id"] == "INST-B"
    # execution 接收到 diagnosis 与 schedule_adjustment
    assert captured_args["diagnosis"] == {"root_causes": ["m"]}
    assert captured_args["schedule_adjustment"]["urgent_order_no"].startswith("URGENT-FAULT")


# ---------------------------------------------------------------------------
# 部分失败场景
# ---------------------------------------------------------------------------


async def test_graph_maintenance_fails_others_run(monkeypatch):
    """maintenance 失败时，quality 与 scheduler 仍应执行（无短路）。"""
    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_maintenance",
        AsyncMock(side_effect=AgentUnavailable("maintenance", "down")),
    )
    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_quality",
        AsyncMock(return_value={"device_id": 7, "root_causes": ["q"]}),
    )
    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_scheduler",
        AsyncMock(
            return_value={
                "urgent_order_no": "x",
                "affected_orders": [],
                "estimated_delay_hours": 0.0,
                "adjustment_plan": {},
            }
        ),
    )
    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_execution",
        AsyncMock(return_value=[{"instruction_id": "INST-1", "type": "REPAIR"}]),
    )
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(return_value="partial summary")
    monkeypatch.setattr("agent_orchestrator.nodes.llm_client", mock_llm)

    result = await app_graph.ainvoke(_initial_state())

    assert result["diagnosis"] is None
    assert result["quality_assessment"] is not None
    assert result["schedule_adjustment"] is not None
    # execution 仍基于 schedule_adjustment 生成指令
    assert result["instructions"] == [{"instruction_id": "INST-1", "type": "REPAIR"}]
    assert result["errors"]["maintenance"] == "down"
    assert "quality" not in result["errors"]
    assert "scheduler" not in result["errors"]
    assert "execution" not in result["errors"]


async def test_graph_all_subagents_fail(monkeypatch):
    """三个子 Agent 全部失败：errors 累积三个 key，summary 仍生成。"""
    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_maintenance",
        AsyncMock(side_effect=AgentUnavailable("maintenance", "m-down")),
    )
    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_quality",
        AsyncMock(side_effect=AgentUnavailable("quality", "q-down")),
    )
    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_scheduler",
        AsyncMock(side_effect=AgentUnavailable("scheduler", "s-down")),
    )
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(return_value="all failed summary")
    monkeypatch.setattr("agent_orchestrator.nodes.llm_client", mock_llm)

    result = await app_graph.ainvoke(_initial_state())

    assert result["diagnosis"] is None
    assert result["quality_assessment"]["status"] == "skipped"
    assert result["schedule_adjustment"]["status"] == "skipped"
    # 三个错误都应被保留（验证读后合并策略）
    assert set(result["errors"].keys()) == {"maintenance", "quality", "scheduler"}
    assert result["errors"]["maintenance"] == "m-down"
    assert result["errors"]["quality"] == "q-down"
    assert result["errors"]["scheduler"] == "s-down"
    # execution 节点 short-circuit（diagnosis/schedule 均空或 skipped），不生成指令、不调 execution
    assert result["instructions"] == []
    assert "execution" not in result["errors"]
    # summary 节点仍执行
    assert result["summary"] == "all failed summary"


async def test_graph_summary_llm_failure(monkeypatch):
    """summary 节点 LLM 失败时降级，不影响其他节点结果。"""
    _patch_all_success(monkeypatch)
    # 覆盖 LLM chat 抛出 LLMClientError
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(side_effect=LLMClientError("llm down"))
    monkeypatch.setattr("agent_orchestrator.nodes.llm_client", mock_llm)

    result = await app_graph.ainvoke(_initial_state())

    assert result["diagnosis"] is not None
    assert result["quality_assessment"] is not None
    assert result["schedule_adjustment"] is not None
    assert result["summary"] == "摘要生成失败，详见各节点结果。"
    # summary 失败不应写入 errors
    assert "summary" not in result["errors"]


async def test_graph_maintenance_and_scheduler_fail_quality_succeeds(monkeypatch):
    """maintenance 与 scheduler 失败、quality 成功：errors 含两个 key。"""
    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_maintenance",
        AsyncMock(side_effect=AgentUnavailable("maintenance", "m-down")),
    )
    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_quality",
        AsyncMock(return_value={"device_id": 7, "root_causes": ["q"]}),
    )
    monkeypatch.setattr(
        "agent_orchestrator.nodes.agent_clients.call_scheduler",
        AsyncMock(side_effect=AgentUnavailable("scheduler", "s-down")),
    )
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(return_value="summary")
    monkeypatch.setattr("agent_orchestrator.nodes.llm_client", mock_llm)

    result = await app_graph.ainvoke(_initial_state())

    assert result["diagnosis"] is None
    assert result["quality_assessment"] is not None
    assert result["schedule_adjustment"]["status"] == "skipped"
    assert set(result["errors"].keys()) == {"maintenance", "scheduler"}
