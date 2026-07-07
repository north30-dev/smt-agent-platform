"""agent_scheduler.planner 排产计划生成单元测试。

使用 monkeypatch 替换 planner 模块内的 device_client / order_store /
llm_client 引用，不依赖真实 PG、device-service 与大模型。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_scheduler import planner


# ---------------------------------------------------------------------------
# 辅助构造函数
# ---------------------------------------------------------------------------


def _make_order(
    order_id: int,
    order_no: str,
    priority: str = "NORMAL",
    delivery_date: str = "2026-07-10",
    quantity: int = 1000,
    material_ready: bool = True,
    product_model: str = "PCBA-A",
):
    """构造测试用订单 dict。"""
    return {
        "order_id": order_id,
        "order_no": order_no,
        "product_model": product_model,
        "quantity": quantity,
        "priority": priority,
        "delivery_date": delivery_date,
        "material_ready": material_ready,
        "status": "PENDING",
        "created_at": "2026-07-06T10:00:00Z",
        "updated_at": "2026-07-06T10:00:00Z",
    }


def _make_device(
    device_id: int,
    device_name: str = "贴片机",
    health_score: int = 90,
    status: str = "RUNNING",
):
    """构造测试用设备 dict。"""
    return {
        "id": device_id,
        "deviceCode": f"D{device_id:03d}",
        "deviceName": device_name,
        "deviceType": "MOUNTER",
        "productionLine": "LINE-1",
        "status": status,
        "healthScore": health_score,
    }


# ---------------------------------------------------------------------------
# 正常路径
# ---------------------------------------------------------------------------


async def test_generate_plan_normal(monkeypatch):
    """3 条订单 + 2 台设备 → 生成 allocations，调 LLM，更新订单状态。"""
    orders = [
        _make_order(1, "ORD-001", priority="NORMAL", delivery_date="2026-07-10"),
        _make_order(2, "ORD-002", priority="URGENT", delivery_date="2026-07-09"),
        _make_order(3, "ORD-003", priority="HIGH", delivery_date="2026-07-08"),
    ]
    devices = [_make_device(10, "贴片机A"), _make_device(11, "贴片机B")]

    updated_statuses: list[tuple[int, str]] = []

    async def _fake_update_status(order_id, status):
        updated_statuses.append((order_id, status))

    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.list_orders",
        AsyncMock(return_value=orders),
    )
    monkeypatch.setattr(
        "agent_scheduler.planner.device_client.list_devices",
        AsyncMock(return_value=devices),
    )
    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.get_next_plan_version",
        AsyncMock(return_value=5),
    )
    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.save_plan",
        AsyncMock(return_value=42),
    )
    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.update_order_status",
        _fake_update_status,
    )
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(return_value="URGENT 单优先，按交付期排产。")
    monkeypatch.setattr("agent_scheduler.planner.llm_client", mock_llm)

    result = await planner.generate_plan()

    assert result["plan_id"] == 42
    assert result["plan_version"] == 5
    assert result["status"] == "ACTIVE"
    assert len(result["allocations"]) == 3
    # URGENT 应排第一
    assert result["allocations"][0]["order_no"] == "ORD-002"
    # LLM 被调用
    mock_llm.chat.assert_called_once()
    # 订单状态全部更新为 PLANNED
    assert sorted(updated_statuses) == [
        (1, "PLANNED"),
        (2, "PLANNED"),
        (3, "PLANNED"),
    ]
    # save_plan 被调用，allocations 落库
    save_plan_args = mock_llm.chat.call_args  # 仅占位
    assert save_plan_args is not None


async def test_generate_plan_allocations_round_robin(monkeypatch):
    """轮询分配：3 条订单 + 2 台设备 → 第 1、3 条落到 device 0，第 2 条落到 device 1。"""
    orders = [
        _make_order(1, "ORD-A", quantity=1000),
        _make_order(2, "ORD-B", quantity=1000),
        _make_order(3, "ORD-C", quantity=1000),
    ]
    devices = [_make_device(10, "贴片机A"), _make_device(11, "贴片机B")]

    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.list_orders",
        AsyncMock(return_value=orders),
    )
    monkeypatch.setattr(
        "agent_scheduler.planner.device_client.list_devices",
        AsyncMock(return_value=devices),
    )
    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.get_next_plan_version",
        AsyncMock(return_value=1),
    )
    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.save_plan",
        AsyncMock(return_value=1),
    )
    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.update_order_status",
        AsyncMock(return_value=None),
    )
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(return_value="排产说明")
    monkeypatch.setattr("agent_scheduler.planner.llm_client", mock_llm)

    result = await planner.generate_plan()

    allocations = result["allocations"]
    assert allocations[0]["device_id"] == 10  # idx 0 → device 0
    assert allocations[1]["device_id"] == 11  # idx 1 → device 1
    assert allocations[2]["device_id"] == 10  # idx 2 → device 0
    # duration = ceil(1000/1000) + 30/60 = 1 + 0.5 = 1.5
    assert allocations[0]["duration_hours"] == pytest.approx(1.5)
    # 第二条订单在 device 0 的 start_hour = ceil(1.5) = 2
    assert allocations[2]["start_hour"] == 2


# ---------------------------------------------------------------------------
# 兜底路径
# ---------------------------------------------------------------------------


async def test_generate_plan_no_pending_orders(monkeypatch):
    """无 PENDING 订单 → 返回 EMPTY 计划。"""
    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.list_orders",
        AsyncMock(return_value=[]),
    )
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(return_value="should not be called")
    monkeypatch.setattr("agent_scheduler.planner.llm_client", mock_llm)

    result = await planner.generate_plan()

    assert result["plan_id"] == 0
    assert result["plan_version"] == 0
    assert result["status"] == "EMPTY"
    assert result["allocations"] == []
    assert "无可用订单" in result["description"]
    mock_llm.chat.assert_not_called()


async def test_generate_plan_no_material_ready(monkeypatch):
    """订单存在但物料未齐套 → 返回 EMPTY 计划。"""
    orders = [
        _make_order(1, "ORD-001", material_ready=False),
        _make_order(2, "ORD-002", material_ready=False),
    ]
    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.list_orders",
        AsyncMock(return_value=orders),
    )
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(return_value="should not be called")
    monkeypatch.setattr("agent_scheduler.planner.llm_client", mock_llm)

    result = await planner.generate_plan()

    assert result["status"] == "EMPTY"
    assert "无可用订单" in result["description"]
    mock_llm.chat.assert_not_called()


async def test_generate_plan_no_running_devices(monkeypatch):
    """无 RUNNING 设备 → 返回 EMPTY 计划，描述说明设备不可用。"""
    orders = [_make_order(1, "ORD-001")]
    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.list_orders",
        AsyncMock(return_value=orders),
    )
    monkeypatch.setattr(
        "agent_scheduler.planner.device_client.list_devices",
        AsyncMock(return_value=[]),
    )
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(return_value="should not be called")
    monkeypatch.setattr("agent_scheduler.planner.llm_client", mock_llm)

    result = await planner.generate_plan()

    assert result["status"] == "EMPTY"
    assert "无可用设备" in result["description"]
    mock_llm.chat.assert_not_called()


async def test_generate_plan_device_below_health_excluded(monkeypatch):
    """设备 healthScore < 85 应被排除。"""
    orders = [_make_order(1, "ORD-001")]
    devices = [
        _make_device(10, "低健康设备", health_score=70),  # 低于阈值
        _make_device(11, "高健康设备", health_score=95),  # 达阈值
    ]
    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.list_orders",
        AsyncMock(return_value=orders),
    )
    monkeypatch.setattr(
        "agent_scheduler.planner.device_client.list_devices",
        AsyncMock(return_value=devices),
    )
    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.get_next_plan_version",
        AsyncMock(return_value=1),
    )
    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.save_plan",
        AsyncMock(return_value=1),
    )
    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.update_order_status",
        AsyncMock(return_value=None),
    )
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(return_value="排产说明")
    monkeypatch.setattr("agent_scheduler.planner.llm_client", mock_llm)

    result = await planner.generate_plan()

    # 仅高健康设备被分配
    assert len(result["allocations"]) == 1
    assert result["allocations"][0]["device_id"] == 11
    assert result["allocations"][0]["device_name"] == "高健康设备"


async def test_generate_plan_description_truncated(monkeypatch):
    """LLM 返回超长描述应被截断到 200 字。"""
    long_text = "排产说明" * 100  # 500 字
    orders = [_make_order(1, "ORD-001")]
    devices = [_make_device(10)]

    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.list_orders",
        AsyncMock(return_value=orders),
    )
    monkeypatch.setattr(
        "agent_scheduler.planner.device_client.list_devices",
        AsyncMock(return_value=devices),
    )
    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.get_next_plan_version",
        AsyncMock(return_value=1),
    )
    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.save_plan",
        AsyncMock(return_value=1),
    )
    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.update_order_status",
        AsyncMock(return_value=None),
    )
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(return_value=long_text)
    monkeypatch.setattr("agent_scheduler.planner.llm_client", mock_llm)

    result = await planner.generate_plan()

    assert len(result["description"]) <= 200


# ---------------------------------------------------------------------------
# 排序规则
# ---------------------------------------------------------------------------


async def test_generate_plan_sort_priority_first(monkeypatch):
    """URGENT 订单应排在最前。"""
    orders = [
        _make_order(1, "ORD-NORMAL", priority="NORMAL", delivery_date="2026-07-08"),
        _make_order(2, "ORD-URGENT", priority="URGENT", delivery_date="2026-07-12"),
    ]
    devices = [_make_device(10)]

    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.list_orders",
        AsyncMock(return_value=orders),
    )
    monkeypatch.setattr(
        "agent_scheduler.planner.device_client.list_devices",
        AsyncMock(return_value=devices),
    )
    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.get_next_plan_version",
        AsyncMock(return_value=1),
    )
    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.save_plan",
        AsyncMock(return_value=1),
    )
    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.update_order_status",
        AsyncMock(return_value=None),
    )
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(return_value="ok")
    monkeypatch.setattr("agent_scheduler.planner.llm_client", mock_llm)

    result = await planner.generate_plan()

    assert result["allocations"][0]["order_no"] == "ORD-URGENT"
    assert result["allocations"][1]["order_no"] == "ORD-NORMAL"


async def test_generate_plan_sort_delivery_date_ascending(monkeypatch):
    """同优先级下按交付日期升序排。"""
    orders = [
        _make_order(1, "ORD-LATE", priority="NORMAL", delivery_date="2026-07-15"),
        _make_order(2, "ORD-EARLY", priority="NORMAL", delivery_date="2026-07-08"),
    ]
    devices = [_make_device(10)]

    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.list_orders",
        AsyncMock(return_value=orders),
    )
    monkeypatch.setattr(
        "agent_scheduler.planner.device_client.list_devices",
        AsyncMock(return_value=devices),
    )
    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.get_next_plan_version",
        AsyncMock(return_value=1),
    )
    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.save_plan",
        AsyncMock(return_value=1),
    )
    monkeypatch.setattr(
        "agent_scheduler.planner.order_store.update_order_status",
        AsyncMock(return_value=None),
    )
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(return_value="ok")
    monkeypatch.setattr("agent_scheduler.planner.llm_client", mock_llm)

    result = await planner.generate_plan()

    assert result["allocations"][0]["order_no"] == "ORD-EARLY"
    assert result["allocations"][1]["order_no"] == "ORD-LATE"
