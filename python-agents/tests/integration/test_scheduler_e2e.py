"""调度智能体端到端集成测试。

验证订单管理、排产计划生成、急单响应的完整链路。
需要 device-service + agent-scheduler + PostgreSQL + LLM 运行。

环境受限时（服务不可达）自动 skip。
"""

import os
import time

import httpx
import pytest

DEVICE_BASE = os.getenv("E2E_DEVICE_BASE", "http://localhost:8081")
SCHEDULER_BASE = os.getenv("E2E_SCHEDULER_BASE", "http://localhost:8001")


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
    if not _service_available(DEVICE_BASE) or not _service_available(SCHEDULER_BASE):
        pytest.skip("device-service 或 agent-scheduler 不可达")


@pytest.mark.integration
def test_order_crud_e2e():
    """创建订单 → 查询订单列表 → 验证状态。"""
    order_no = f"E2E-ORD-{int(time.time())}"
    create_resp = httpx.post(
        f"{SCHEDULER_BASE}/v1/scheduler/orders",
        json={
            "order_no": order_no,
            "product_model": "SMT-PCB-A",
            "quantity": 1000,
            "priority": "NORMAL",
            "delivery_date": "2026-08-01",
            "material_ready": True,
        },
        timeout=10.0,
    )
    assert create_resp.status_code == 200, f"订单创建失败: {create_resp.text}"
    order = create_resp.json()
    assert order["order_no"] == order_no
    assert order["status"] == "PENDING"

    # 查询订单列表
    list_resp = httpx.get(f"{SCHEDULER_BASE}/v1/scheduler/orders", timeout=10.0)
    assert list_resp.status_code == 200, f"订单查询失败: {list_resp.text}"
    data = list_resp.json()
    assert "records" in data
    assert "total" in data
    assert any(r["order_no"] == order_no for r in data["records"])


@pytest.mark.integration
def test_plan_generate_e2e():
    """创建订单 → 生成排产计划 → 查询当前计划 → 验证 allocations。"""
    order_no = f"E2E-PLN-{int(time.time())}"
    httpx.post(
        f"{SCHEDULER_BASE}/v1/scheduler/orders",
        json={
            "order_no": order_no,
            "product_model": "SMT-PCB-B",
            "quantity": 500,
            "priority": "HIGH",
            "delivery_date": "2026-08-05",
            "material_ready": True,
        },
        timeout=10.0,
    )

    # 生成排产计划
    gen_resp = httpx.post(
        f"{SCHEDULER_BASE}/v1/scheduler/plan/generate",
        json={"force_regenerate": True},
        timeout=120.0,
    )
    assert gen_resp.status_code == 200, f"排产生成失败: {gen_resp.text}"
    plan = gen_resp.json()
    assert "plan_id" in plan
    assert "allocations" in plan
    assert isinstance(plan["allocations"], list)

    # 查询当前计划
    current_resp = httpx.get(f"{SCHEDULER_BASE}/v1/scheduler/plan/current", timeout=10.0)
    assert current_resp.status_code == 200, f"当前计划查询失败: {current_resp.text}"
    current = current_resp.json()
    assert "plan_id" in current
    assert "allocations" in current


@pytest.mark.integration
def test_urgent_response_e2e():
    """提交急单 → 验证返回调整方案和影响评估。"""
    resp = httpx.post(
        f"{SCHEDULER_BASE}/v1/scheduler/urgent",
        json={
            "order_no": f"E2E-URG-{int(time.time())}",
            "product_model": "SMT-PCB-C",
            "quantity": 200,
            "delivery_date": "2026-07-20",
            "source": "user",
        },
        timeout=60.0,
    )
    assert resp.status_code == 200, f"急单响应失败: {resp.text}"
    data = resp.json()
    assert "urgent_order_no" in data
    assert "affected_orders" in data
    assert "estimated_delay_hours" in data
    assert "adjustment_plan" in data
    assert "changeover_suggestion" in data["adjustment_plan"]
    assert "overtime_suggestion" in data["adjustment_plan"]
