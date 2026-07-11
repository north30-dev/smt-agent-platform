"""端到端集成测试（smoke）。

补齐 phase2 报告 B-7 盲区：无端到端集成测试。
需要 docker-compose 启动真实中间件 + Java device-service + Python agents 运行。
标记 @pytest.mark.integration，常规 pytest 不跑，需用 `pytest -m integration` 显式触发。

环境受限时（服务不可达）自动 skip，不记为失败。
"""

import os

import httpx
import pytest

# 服务地址（与 docker-compose/dev profile 对齐）
KNOWLEDGE_BASE = os.getenv("E2E_KNOWLEDGE_BASE", "http://localhost:8004")
MAINTENANCE_BASE = os.getenv("E2E_MAINTENANCE_BASE", "http://localhost:8002")
DEVICE_BASE = os.getenv("E2E_DEVICE_BASE", "http://localhost:8081")
GATEWAY_BASE = os.getenv("E2E_GATEWAY_BASE", "http://localhost:8080")


def _service_available(url: str) -> bool:
    """检查服务是否可达（3 秒超时）。

    FastAPI 用 /docs，Spring Boot 用 /actuator/health。
    """
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
    """服务不可达时自动 skip。"""
    if not _service_available(KNOWLEDGE_BASE):
        pytest.skip(f"knowledge service 不可达: {KNOWLEDGE_BASE}", allow_module_level=False)


@pytest.mark.integration
def test_knowledge_upload_and_ask_e2e():
    """端到端：上传 md 文档 → ask 问答 → 验证返回非空 answer。

    需要真实 Milvus + LLM 服务运行。
    """
    sample_content = "# SMT 维护手册\n\n钢网清洁：每班次生产结束后使用专用清洗剂。".encode("utf-8")
    upload_resp = httpx.post(
        f"{KNOWLEDGE_BASE}/v1/knowledge/upload",
        files={"file": ("e2e_sample.md", sample_content, "text/markdown")},
        timeout=30.0,
    )
    assert upload_resp.status_code == 200, f"上传失败: {upload_resp.text}"
    doc_id = upload_resp.json()["doc_id"]
    assert doc_id

    ask_resp = httpx.post(
        f"{KNOWLEDGE_BASE}/v1/knowledge/ask",
        json={"question": "钢网清洁频率是多少？"},
        timeout=60.0,
    )
    assert ask_resp.status_code == 200, f"问答失败: {ask_resp.text}"
    answer = ask_resp.json()["answer"]
    assert isinstance(answer, str) and len(answer) > 0


@pytest.mark.integration
def test_maintenance_health_e2e():
    """端到端：通过 device-service 创建设备 → maintenance/health 查询 → 验证字段映射。

    需要 device-service + maintenance agent 运行。
    """
    if not _service_available(DEVICE_BASE) or not _service_available(MAINTENANCE_BASE):
        pytest.skip("device-service 或 maintenance agent 不可达")

    # 1. 通过 device-service 创建设备
    create_resp = httpx.post(
        f"{DEVICE_BASE}/api/device",
        json={
            "deviceCode": "E2E-TEST-001",
            "deviceName": "E2E 测试设备",
            "deviceType": "PRINTER",
            "productionLine": "LINE-E2E",
            "ipAddress": "127.0.0.1",
            "protocolType": "MQTT",
            "status": "RUNNING",
        },
        timeout=10.0,
    )
    if create_resp.status_code != 200:
        # 设备可能已存在，尝试查询
        list_resp = httpx.get(f"{DEVICE_BASE}/api/device/list?size=1", timeout=10.0)
        assert list_resp.status_code == 200
        records = list_resp.json().get("data", {}).get("records", [])
        if not records:
            pytest.skip("无法创建或查询设备")
        device_id = records[0]["id"]
    else:
        device_id = create_resp.json()["data"]["id"]

    # 2. 通过 maintenance agent 查询健康评分
    health_resp = httpx.get(
        f"{MAINTENANCE_BASE}/v1/maintenance/health/{device_id}",
        timeout=10.0,
    )
    assert health_resp.status_code == 200, f"health 查询失败: {health_resp.text}"
    data = health_resp.json()

    # 3. 验证字段映射：Java camelCase healthScore → Python snake_case health_score
    assert "health_score" in data
    assert "device_id" in data
    assert "risk_level" in data
    assert data["device_id"] == device_id
