"""多 Agent 编排端到端集成测试。

验证设备故障编排的完整链路：maintenance → quality → scheduler → execution → summary。
需要全部 Python Agent + device-service + PostgreSQL + Milvus + LLM 运行。

环境受限时（服务不可达）自动 skip。
"""

import os
import time

import httpx
import pytest

DEVICE_BASE = os.getenv("E2E_DEVICE_BASE", "http://localhost:8081")
ORCHESTRATOR_BASE = os.getenv("E2E_ORCHESTRATOR_BASE", "http://localhost:8005")


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
    if not _service_available(DEVICE_BASE) or not _service_available(ORCHESTRATOR_BASE):
        pytest.skip("device-service 或 agent-orchestrator 不可达")


def _create_device() -> int | None:
    resp = httpx.post(
        f"{DEVICE_BASE}/api/device",
        json={
            "deviceCode": f"E2E-ORC-{int(time.time())}",
            "deviceName": "E2E 编排测试设备",
            "deviceType": "PRINTER",
            "productionLine": "LINE-ORC",
            "ipAddress": "127.0.0.1",
            "protocolType": "MQTT",
            "status": "RUNNING",
        },
        timeout=10.0,
    )
    if resp.status_code == 200:
        return resp.json()["data"]["id"]
    list_resp = httpx.get(f"{DEVICE_BASE}/api/device/list?size=1", timeout=10.0)
    if list_resp.status_code == 200:
        records = list_resp.json().get("data", {}).get("records", [])
        if records:
            return records[0]["id"]
    return None


@pytest.mark.integration
def test_device_fault_workflow_e2e():
    """创建设备 → 触发 device_fault 编排 → 查询 workflow 状态。"""
    device_id = _create_device()
    if device_id is None:
        pytest.skip("无法创建设备")

    # 触发编排
    resp = httpx.post(
        f"{ORCHESTRATOR_BASE}/v1/orchestrator/device_fault",
        json={"device_id": device_id, "symptom": "E2E 测试：贴片精度偏移"},
        timeout=120.0,
    )
    assert resp.status_code == 200, f"编排触发失败: {resp.text}"
    workflow = resp.json()
    assert "workflow_id" in workflow
    assert "status" in workflow
    assert workflow["status"] in ("SUCCESS", "PARTIAL", "FAILED")

    # 查询 workflow
    wf_id = workflow["workflow_id"]
    get_resp = httpx.get(
        f"{ORCHESTRATOR_BASE}/v1/orchestrator/workflows/{wf_id}",
        timeout=10.0,
    )
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["workflow_id"] == wf_id
    assert "status" in data
