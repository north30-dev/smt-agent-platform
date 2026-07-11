"""网关路由端到端集成测试。

验证 smt-gateway 路由转发和 JWT 鉴权的完整链路。
需要 smt-gateway + 各 Agent 运行。

环境受限时（服务不可达）自动 skip。
"""

import os

import httpx
import pytest

GATEWAY_BASE = os.getenv("E2E_GATEWAY_BASE", "http://localhost:8080")
DEVICE_BASE = os.getenv("E2E_DEVICE_BASE", "http://localhost:8081")


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
    if not _service_available(GATEWAY_BASE):
        pytest.skip("smt-gateway 不可达")


@pytest.mark.integration
def test_gateway_proxy_device_service_e2e():
    """通过 gateway 访问 device-service（不走 JWT 鉴权的路由）。"""
    if not _service_available(DEVICE_BASE):
        pytest.skip("device-service 不可达")

    resp = httpx.get(f"{GATEWAY_BASE}/api/device/list?size=1", timeout=10.0)
    assert resp.status_code == 200, f"网关代理 device-service 失败: {resp.status_code}"
    data = resp.json()
    assert "data" in data


@pytest.mark.integration
def test_gateway_jwt_auth_e2e():
    """无 token 请求受保护路由 → 验证 401/403。"""
    resp = httpx.get(f"{GATEWAY_BASE}/api/agent/v1/knowledge/documents", timeout=10.0)
    assert resp.status_code in (401, 403), f"预期 401/403，实际 {resp.status_code}"


@pytest.mark.integration
def test_gateway_jwt_auth_maintenance_e2e():
    """无 token 请求 maintenance 受保护路由 → 验证 401/403。"""
    resp = httpx.get(f"{GATEWAY_BASE}/api/agent/v1/maintenance/health/1", timeout=10.0)
    assert resp.status_code in (401, 403), f"预期 401/403，实际 {resp.status_code}"


@pytest.mark.integration
def test_gateway_jwt_auth_quality_e2e():
    """无 token 请求 quality 受保护路由 → 验证 401/403。"""
    resp = httpx.get(f"{GATEWAY_BASE}/api/agent/v1/quality/alerts", timeout=10.0)
    assert resp.status_code in (401, 403), f"预期 401/403，实际 {resp.status_code}"


@pytest.mark.integration
def test_gateway_jwt_auth_scheduler_e2e():
    """无 token 请求 scheduler 受保护路由 → 验证 401/403。"""
    resp = httpx.get(f"{GATEWAY_BASE}/api/agent/v1/scheduler/orders", timeout=10.0)
    assert resp.status_code in (401, 403), f"预期 401/403，实际 {resp.status_code}"


@pytest.mark.integration
def test_gateway_jwt_auth_execution_e2e():
    """无 token 请求 execution 受保护路由 → 验证 401/403。"""
    resp = httpx.get(f"{GATEWAY_BASE}/api/agent/v1/execution/instructions", timeout=10.0)
    assert resp.status_code in (401, 403), f"预期 401/403，实际 {resp.status_code}"
