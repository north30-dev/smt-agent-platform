"""agent_scheduler.urgent 急单插单单元测试。

使用 monkeypatch 替换 urgent 模块内的 order_store / llm_client 引用，
不依赖真实 PG 与大模型。
"""

import json
from unittest.mock import AsyncMock, MagicMock

from agent_scheduler import urgent
from agent_scheduler.models import UrgentRequest


# ---------------------------------------------------------------------------
# 辅助构造函数
# ---------------------------------------------------------------------------


def _make_urgent_request(
    order_no: str = "URGENT-001",
    product_model: str = "PCBA-B",
    quantity: int = 2000,
    delivery_date: str = "2026-07-08",
) -> UrgentRequest:
    return UrgentRequest(
        order_no=order_no,
        product_model=product_model,
        quantity=quantity,
        delivery_date=delivery_date,
    )


def _make_current_plan(allocations: list[dict]) -> dict:
    """构造当前 ACTIVE 计划。"""
    return {
        "plan_id": 1,
        "plan_version": 1,
        "allocations": allocations,
        "description": "当前计划",
        "status": "ACTIVE",
        "created_at": "2026-07-06T10:00:00Z",
    }


def _make_allocation(
    order_no: str,
    product_model: str = "PCBA-A",
    device_id: int = 10,
    start_hour: int = 0,
    duration_hours: float = 1.5,
) -> dict:
    return {
        "order_no": order_no,
        "product_model": product_model,
        "device_id": device_id,
        "device_name": f"贴片机{device_id}",
        "start_hour": start_hour,
        "duration_hours": duration_hours,
    }


# ---------------------------------------------------------------------------
# 正常路径
# ---------------------------------------------------------------------------


async def test_handle_urgent_normal(monkeypatch):
    """有当前计划 + 受影响订单 + LLM 返回有效 JSON → 正常响应。"""
    saved_orders = []

    async def _fake_save_order(**kwargs):
        saved_orders.append(kwargs)
        return 100

    monkeypatch.setattr(
        "agent_scheduler.urgent.order_store.save_order",
        _fake_save_order,
    )
    monkeypatch.setattr(
        "agent_scheduler.urgent.order_store.get_current_plan",
        AsyncMock(
            return_value=_make_current_plan(
                [
                    _make_allocation("ORD-001", start_hour=0),
                    _make_allocation("ORD-002", start_hour=2),
                ]
            )
        ),
    )
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(
        return_value=json.dumps(
            {
                "changeover_suggestion": "切换至产品 B，调整 SPI 参数",
                "overtime_suggestion": "晚班加班 2 小时",
            },
            ensure_ascii=False,
        )
    )
    monkeypatch.setattr("agent_scheduler.urgent.llm_client", mock_llm)

    req = _make_urgent_request(quantity=2000)
    result = await urgent.handle_urgent(req)

    # 急单落库
    assert len(saved_orders) == 1
    assert saved_orders[0]["priority"] == "URGENT"
    assert saved_orders[0]["material_ready"] is True
    assert saved_orders[0]["order_no"] == "URGENT-001"

    # 受影响订单：start_hour=0 的 ORD-001 受影响（duration=2+0.5=2.5 > 0），
    # start_hour=2 的 ORD-002 受影响（2 < 2.5）
    assert len(result["affected_orders"]) == 2
    assert result["affected_orders"][0]["order_no"] == "ORD-001"
    assert result["affected_orders"][1]["order_no"] == "ORD-002"
    # 延迟 = 2.5 * 2 = 5.0
    assert result["estimated_delay_hours"] == 5.0

    # 调整方案来自 LLM
    assert result["adjustment_plan"]["changeover_suggestion"] == "切换至产品 B，调整 SPI 参数"
    assert result["adjustment_plan"]["overtime_suggestion"] == "晚班加班 2 小时"

    # LLM 被调用
    mock_llm.chat.assert_called_once()


async def test_handle_urgent_partial_affected(monkeypatch):
    """仅部分订单受影响 → affected_orders 仅含被影响项。"""
    monkeypatch.setattr(
        "agent_scheduler.urgent.order_store.save_order",
        AsyncMock(return_value=100),
    )
    monkeypatch.setattr(
        "agent_scheduler.urgent.order_store.get_current_plan",
        AsyncMock(
            return_value=_make_current_plan(
                [
                    _make_allocation("ORD-A", start_hour=0),
                    _make_allocation("ORD-B", start_hour=10),  # 不受影响
                    _make_allocation("ORD-C", start_hour=20),  # 不受影响
                ]
            )
        ),
    )
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(
        return_value=json.dumps(
            {"changeover_suggestion": "换线", "overtime_suggestion": "加班"}
        )
    )
    monkeypatch.setattr("agent_scheduler.urgent.llm_client", mock_llm)

    # quantity=1000 → duration = ceil(1000/1000) + 0.5 = 1.5
    req = _make_urgent_request(quantity=1000)
    result = await urgent.handle_urgent(req)

    assert len(result["affected_orders"]) == 1
    assert result["affected_orders"][0]["order_no"] == "ORD-A"
    # 延迟 = 1.5 * 1 = 1.5
    assert result["estimated_delay_hours"] == 1.5


async def test_handle_urgent_no_current_plan(monkeypatch):
    """无当前计划 → affected_orders 为空，返回默认建议。"""
    monkeypatch.setattr(
        "agent_scheduler.urgent.order_store.save_order",
        AsyncMock(return_value=100),
    )
    monkeypatch.setattr(
        "agent_scheduler.urgent.order_store.get_current_plan",
        AsyncMock(return_value=None),
    )
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(return_value="should not be called")
    monkeypatch.setattr("agent_scheduler.urgent.llm_client", mock_llm)

    req = _make_urgent_request()
    result = await urgent.handle_urgent(req)

    assert result["urgent_order_no"] == "URGENT-001"
    assert result["affected_orders"] == []
    assert result["estimated_delay_hours"] == 0.0
    assert "可直接排入" in result["adjustment_plan"]["changeover_suggestion"]
    assert "无需加班" in result["adjustment_plan"]["overtime_suggestion"]
    mock_llm.chat.assert_not_called()


# ---------------------------------------------------------------------------
# LLM 输出解析降级
# ---------------------------------------------------------------------------


async def test_handle_urgent_llm_malformed_json(monkeypatch):
    """LLM 返回非 JSON → 降级为占位提示，不抛异常。"""
    monkeypatch.setattr(
        "agent_scheduler.urgent.order_store.save_order",
        AsyncMock(return_value=100),
    )
    monkeypatch.setattr(
        "agent_scheduler.urgent.order_store.get_current_plan",
        AsyncMock(
            return_value=_make_current_plan(
                [_make_allocation("ORD-A", start_hour=0)]
            )
        ),
    )
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(return_value="无法解析的纯文本")
    monkeypatch.setattr("agent_scheduler.urgent.llm_client", mock_llm)

    req = _make_urgent_request(quantity=1000)
    result = await urgent.handle_urgent(req)

    # 受影响订单仍正常计算
    assert len(result["affected_orders"]) == 1
    # 调整方案降级
    assert "无法解析" in result["adjustment_plan"]["changeover_suggestion"]
    assert "LLM 输出解析失败" in result["adjustment_plan"]["overtime_suggestion"]


async def test_handle_urgent_llm_json_in_codeblock(monkeypatch):
    """LLM 输出 markdown 代码块包裹的 JSON → 应正确解析。"""
    monkeypatch.setattr(
        "agent_scheduler.urgent.order_store.save_order",
        AsyncMock(return_value=100),
    )
    monkeypatch.setattr(
        "agent_scheduler.urgent.order_store.get_current_plan",
        AsyncMock(
            return_value=_make_current_plan(
                [_make_allocation("ORD-A", start_hour=0)]
            )
        ),
    )
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(
        return_value=(
            "分析如下：\n"
            "```json\n"
            '{"changeover_suggestion": "换线建议 A", '
            '"overtime_suggestion": "加班建议 B"}\n'
            "```"
        )
    )
    monkeypatch.setattr("agent_scheduler.urgent.llm_client", mock_llm)

    req = _make_urgent_request(quantity=1000)
    result = await urgent.handle_urgent(req)

    assert result["adjustment_plan"]["changeover_suggestion"] == "换线建议 A"
    assert result["adjustment_plan"]["overtime_suggestion"] == "加班建议 B"


async def test_handle_urgent_llm_partial_fields(monkeypatch):
    """LLM 返回 JSON 但缺字段 → 缺失字段补默认提示。"""
    monkeypatch.setattr(
        "agent_scheduler.urgent.order_store.save_order",
        AsyncMock(return_value=100),
    )
    monkeypatch.setattr(
        "agent_scheduler.urgent.order_store.get_current_plan",
        AsyncMock(
            return_value=_make_current_plan(
                [_make_allocation("ORD-A", start_hour=0)]
            )
        ),
    )
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(
        return_value=json.dumps({"changeover_suggestion": "仅换线建议"})
    )
    monkeypatch.setattr("agent_scheduler.urgent.llm_client", mock_llm)

    req = _make_urgent_request(quantity=1000)
    result = await urgent.handle_urgent(req)

    assert result["adjustment_plan"]["changeover_suggestion"] == "仅换线建议"
    assert "未给出" in result["adjustment_plan"]["overtime_suggestion"]


# ---------------------------------------------------------------------------
# 时长估算
# ---------------------------------------------------------------------------


async def test_handle_urgent_duration_calculation(monkeypatch):
    """duration = ceil(quantity/capacity) + changeover_minutes/60。"""
    # capacity_per_hour=1000，changeover_minutes=30
    # quantity=2500 → ceil(2500/1000)=3 + 0.5 = 3.5
    monkeypatch.setattr(
        "agent_scheduler.urgent.order_store.save_order",
        AsyncMock(return_value=100),
    )
    monkeypatch.setattr(
        "agent_scheduler.urgent.order_store.get_current_plan",
        AsyncMock(
            return_value=_make_current_plan(
                [_make_allocation("ORD-A", start_hour=0)]
            )
        ),
    )
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(
        return_value=json.dumps(
            {"changeover_suggestion": "x", "overtime_suggestion": "y"}
        )
    )
    monkeypatch.setattr("agent_scheduler.urgent.llm_client", mock_llm)

    req = _make_urgent_request(quantity=2500)
    result = await urgent.handle_urgent(req)

    # 1 个受影响订单，delay = 3.5
    assert result["estimated_delay_hours"] == 3.5
    assert result["affected_orders"][0]["delay_hours"] == 3.5
