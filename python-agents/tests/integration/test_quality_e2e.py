"""质量分析 Agent 端到端集成测试。

验证质量监控、根因分析、案例录入、告警查询的完整链路。
需要 device-service + agent-quality + PostgreSQL + Milvus + LLM 运行。

环境受限时（服务不可达）自动 skip。
"""

import os
import time

import httpx
import pytest

DEVICE_BASE = os.getenv("E2E_DEVICE_BASE", "http://localhost:8081")
QUALITY_BASE = os.getenv("E2E_QUALITY_BASE", "http://localhost:8003")


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
    if not _service_available(DEVICE_BASE) or not _service_available(QUALITY_BASE):
        pytest.skip("device-service 或 agent-quality 不可达")


def _create_device() -> int | None:
    """创建测试设备，返回 device_id。"""
    resp = httpx.post(
        f"{DEVICE_BASE}/api/device",
        json={
            "deviceCode": f"E2E-QLT-{int(time.time())}",
            "deviceName": "E2E 质量测试设备",
            "deviceType": "AOI",
            "productionLine": "LINE-QLT",
            "ipAddress": "127.0.0.1",
            "protocolType": "MQTT",
            "status": "RUNNING",
        },
        timeout=10.0,
    )
    if resp.status_code == 200:
        return resp.json()["data"]["id"]
    # 设备可能已存在，取第一个
    list_resp = httpx.get(f"{DEVICE_BASE}/api/device/list?size=1", timeout=10.0)
    if list_resp.status_code == 200:
        records = list_resp.json().get("data", {}).get("records", [])
        if records:
            return records[0]["id"]
    return None


@pytest.mark.integration
def test_quality_monitor_e2e():
    """查询设备 AOI 缺陷率监控 → 验证返回结构。"""
    device_id = _create_device()
    if device_id is None:
        pytest.skip("无法创建设备")

    resp = httpx.get(f"{QUALITY_BASE}/v1/quality/monitor/{device_id}", timeout=30.0)
    assert resp.status_code == 200, f"质量监控查询失败: {resp.text}"
    data = resp.json()
    assert "device_id" in data
    assert "defect_rate" in data
    assert "threshold" in data
    assert "status" in data
    assert data["status"] in ("OK", "ALERT", "INSUFFICIENT_DATA")


@pytest.mark.integration
def test_quality_root_cause_e2e():
    """提交缺陷描述 → 根因分析 → 验证返回根因和纠正措施。"""
    device_id = _create_device()
    if device_id is None:
        pytest.skip("无法创建设备")

    resp = httpx.post(
        f"{QUALITY_BASE}/v1/quality/root_cause",
        json={"device_id": device_id, "defect_description": "焊点虚焊，AOI 检测不良率升高"},
        timeout=60.0,
    )
    assert resp.status_code == 200, f"根因分析失败: {resp.text}"
    data = resp.json()
    assert "device_id" in data
    assert "root_causes" in data
    assert isinstance(data["root_causes"], list)
    assert "corrective_actions" in data
    assert isinstance(data["corrective_actions"], list)
    if data["root_causes"]:
        first = data["root_causes"][0]
        assert "category" in first
        assert "cause" in first


@pytest.mark.integration
def test_quality_case_and_alert_e2e():
    """录入质量案例 → 查询告警列表 → 验证分页结构。"""
    # 录入案例
    create_resp = httpx.post(
        f"{QUALITY_BASE}/v1/quality/cases",
        json={
            "defect_type": "虚焊",
            "description": "E2E 测试：焊膏印刷偏移导致虚焊",
            "root_cause": "钢网开口设计不合理",
            "corrective_action": "调整钢网开口尺寸",
        },
        timeout=30.0,
    )
    assert create_resp.status_code == 200, f"案例录入失败: {create_resp.text}"
    case_id = create_resp.json()["case_id"]
    assert case_id

    # 查询告警列表
    alerts_resp = httpx.get(f"{QUALITY_BASE}/v1/quality/alerts?page=1&size=10", timeout=10.0)
    assert alerts_resp.status_code == 200, f"告警查询失败: {alerts_resp.text}"
    data = alerts_resp.json()
    assert "records" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
