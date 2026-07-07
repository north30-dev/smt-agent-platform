"""agent_scheduler.main FastAPI 接口集成测试。

使用 TestClient 调用真实路由，通过 monkeypatch 替换 main 模块中
order_store / planner / urgent 的引用，不触达真实服务。
"""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from agent_scheduler.device_client import DeviceServiceUnavailable
from agent_scheduler.main import app
from shared.llm_client import LLMClientError

client = TestClient(app)


# ---------------------------------------------------------------------------
# /healthz
# ---------------------------------------------------------------------------


def test_healthz_returns_200():
    """/healthz 应返回 200 与 healthy 状态。"""
    response = client.get("/healthz")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["uptime_seconds"] >= 0


# ---------------------------------------------------------------------------
# POST /v1/scheduler/orders
# ---------------------------------------------------------------------------


def test_create_order_returns_200(monkeypatch):
    """订单录入应返回 200 与 PENDING 状态。"""
    monkeypatch.setattr(
        "agent_scheduler.main.order_store.save_order",
        AsyncMock(return_value=42),
    )

    response = client.post(
        "/v1/scheduler/orders",
        json={
            "order_no": "ORD-001",
            "product_model": "PCBA-A",
            "quantity": 5000,
            "priority": "NORMAL",
            "delivery_date": "2026-07-10",
            "material_ready": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["order_id"] == 42
    assert data["order_no"] == "ORD-001"
    assert data["status"] == "PENDING"


def test_create_order_invalid_quantity_returns_422():
    """quantity < 1 应触发 Pydantic 校验失败 → 422。"""
    response = client.post(
        "/v1/scheduler/orders",
        json={
            "order_no": "ORD-001",
            "product_model": "PCBA-A",
            "quantity": 0,
            "priority": "NORMAL",
            "delivery_date": "2026-07-10",
        },
    )

    assert response.status_code == 422


def test_create_order_missing_field_returns_422():
    """缺必填字段 → 422。"""
    response = client.post(
        "/v1/scheduler/orders",
        json={"order_no": "ORD-001"},
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /v1/scheduler/orders
# ---------------------------------------------------------------------------


def test_list_orders_returns_200(monkeypatch):
    """订单列表应返回 200 与 records/total。"""
    fake_records = [
        {
            "order_id": 1,
            "order_no": "ORD-001",
            "product_model": "PCBA-A",
            "quantity": 5000,
            "priority": "NORMAL",
            "delivery_date": "2026-07-10",
            "material_ready": True,
            "status": "PENDING",
            "created_at": "2026-07-06T10:00:00Z",
        },
        {
            "order_id": 2,
            "order_no": "ORD-002",
            "product_model": "PCBA-B",
            "quantity": 2000,
            "priority": "URGENT",
            "delivery_date": "2026-07-08",
            "material_ready": True,
            "status": "PLANNED",
            "created_at": "2026-07-06T11:00:00Z",
        },
    ]
    monkeypatch.setattr(
        "agent_scheduler.main.order_store.list_orders",
        AsyncMock(return_value=fake_records),
    )

    response = client.get("/v1/scheduler/orders")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["records"]) == 2
    assert data["records"][0]["order_no"] == "ORD-001"


def test_list_orders_with_status_filter(monkeypatch):
    """status 过滤应传递给 order_store.list_orders。"""
    captured = {}

    async def _fake_list_orders(status=None):
        captured["status"] = status
        return []

    monkeypatch.setattr(
        "agent_scheduler.main.order_store.list_orders", _fake_list_orders
    )

    response = client.get("/v1/scheduler/orders?status=PENDING")

    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert captured["status"] == "PENDING"


# ---------------------------------------------------------------------------
# POST /v1/scheduler/plan/generate
# ---------------------------------------------------------------------------


def test_generate_plan_returns_200(monkeypatch):
    """生成排产计划应返回 200 与 PlanResponse。"""
    fake_plan = {
        "plan_id": 1,
        "plan_version": 1,
        "allocations": [
            {
                "order_no": "ORD-001",
                "product_model": "PCBA-A",
                "device_id": 10,
                "device_name": "贴片机A",
                "start_hour": 0,
                "duration_hours": 1.5,
            }
        ],
        "description": "排产说明",
        "status": "ACTIVE",
        "created_at": "2026-07-06T10:00:00Z",
    }
    monkeypatch.setattr(
        "agent_scheduler.main.planner.generate_plan",
        AsyncMock(return_value=fake_plan),
    )

    response = client.post("/v1/scheduler/plan/generate", json={})

    assert response.status_code == 200
    data = response.json()
    assert data["plan_id"] == 1
    assert data["plan_version"] == 1
    assert data["status"] == "ACTIVE"
    assert len(data["allocations"]) == 1


def test_generate_plan_device_unavailable_returns_503(monkeypatch):
    """device-service 不可达 → 503。"""
    monkeypatch.setattr(
        "agent_scheduler.main.planner.generate_plan",
        AsyncMock(side_effect=DeviceServiceUnavailable("connection refused")),
    )

    response = client.post("/v1/scheduler/plan/generate", json={})

    assert response.status_code == 503
    data = response.json()
    assert data["error"] == "device_service_unavailable"


def test_generate_plan_llm_error_returns_503(monkeypatch):
    """LLMClientError → 503。"""
    monkeypatch.setattr(
        "agent_scheduler.main.planner.generate_plan",
        AsyncMock(side_effect=LLMClientError("llm timeout")),
    )

    response = client.post("/v1/scheduler/plan/generate", json={})

    assert response.status_code == 503
    assert response.json()["error"] == "llm_unavailable"


# ---------------------------------------------------------------------------
# GET /v1/scheduler/plan/current
# ---------------------------------------------------------------------------


def test_get_current_plan_returns_200(monkeypatch):
    """有 ACTIVE 计划 → 200。"""
    fake_plan = {
        "plan_id": 1,
        "plan_version": 1,
        "allocations": [],
        "description": "已有计划",
        "status": "ACTIVE",
        "created_at": "2026-07-06T10:00:00Z",
    }
    monkeypatch.setattr(
        "agent_scheduler.main.order_store.get_current_plan",
        AsyncMock(return_value=fake_plan),
    )

    response = client.get("/v1/scheduler/plan/current")

    assert response.status_code == 200
    data = response.json()
    assert data["plan_id"] == 1
    assert data["status"] == "ACTIVE"


def test_get_current_plan_returns_404_when_none(monkeypatch):
    """无 ACTIVE 计划 → 404。"""
    monkeypatch.setattr(
        "agent_scheduler.main.order_store.get_current_plan",
        AsyncMock(return_value=None),
    )

    response = client.get("/v1/scheduler/plan/current")

    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "plan_not_found"


# ---------------------------------------------------------------------------
# POST /v1/scheduler/urgent
# ---------------------------------------------------------------------------


def test_handle_urgent_returns_200(monkeypatch):
    """急单插单应返回 200 与 UrgentResponse。"""
    fake_response = {
        "urgent_order_no": "URGENT-001",
        "affected_orders": [
            {
                "order_no": "ORD-001",
                "product_model": "PCBA-A",
                "delay_hours": 2.5,
            }
        ],
        "estimated_delay_hours": 2.5,
        "adjustment_plan": {
            "changeover_suggestion": "切换至产品 B",
            "overtime_suggestion": "晚班加班 2 小时",
        },
    }
    monkeypatch.setattr(
        "agent_scheduler.main.urgent.handle_urgent",
        AsyncMock(return_value=fake_response),
    )

    response = client.post(
        "/v1/scheduler/urgent",
        json={
            "order_no": "URGENT-001",
            "product_model": "PCBA-B",
            "quantity": 2000,
            "delivery_date": "2026-07-08",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["urgent_order_no"] == "URGENT-001"
    assert len(data["affected_orders"]) == 1
    assert data["estimated_delay_hours"] == 2.5
    assert "切换至产品 B" in data["adjustment_plan"]["changeover_suggestion"]


def test_handle_urgent_invalid_quantity_returns_422():
    """quantity < 1 → 422。"""
    response = client.post(
        "/v1/scheduler/urgent",
        json={
            "order_no": "URGENT-001",
            "product_model": "PCBA-B",
            "quantity": 0,
            "delivery_date": "2026-07-08",
        },
    )

    assert response.status_code == 422


def test_handle_urgent_missing_field_returns_422():
    """缺必填字段 → 422。"""
    response = client.post(
        "/v1/scheduler/urgent",
        json={"order_no": "URGENT-001"},
    )

    assert response.status_code == 422
