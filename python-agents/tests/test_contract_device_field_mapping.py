"""Java device-service ↔ Python Agent 字段命名契约守护测试。

补齐 phase2 报告 B-3 盲区：Java 返回 camelCase（healthScore），
Python 响应 snake_case（health_score），映射逻辑靠 main.py 中
`int(device.get("healthScore") or 0)` 实现，此前无显式测试守护。

本测试验证：
1. health 接口响应字段名符合 OpenAPI MaintenanceHealthResponse 契约
2. Java camelCase healthScore 正确映射为 Python snake_case health_score
"""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from agent_maintenance.main import app

client = TestClient(app)

# OpenAPI agent_api.yaml 中 MaintenanceHealthResponse 必填字段
EXPECTED_HEALTH_FIELDS = {"device_id", "health_score", "status", "risk_level", "analysis"}


def test_health_response_field_names_match_openapi(monkeypatch):
    """health 响应字段名应与 OpenAPI MaintenanceHealthResponse 一致（snake_case）。"""
    monkeypatch.setattr(
        "agent_maintenance.main.device_client.get_device",
        AsyncMock(
            return_value={
                "id": 1001,
                "healthScore": 88,
                "status": "RUNNING",
                "deviceName": "贴片机",
            }
        ),
    )

    response = client.get("/maintenance/health/1001")

    assert response.status_code == 200
    data = response.json()
    # 响应字段名应为 snake_case，与 OpenAPI 契约一致
    assert set(data.keys()) == EXPECTED_HEALTH_FIELDS
    # Java camelCase healthScore 应映射为 Python snake_case health_score
    assert data["health_score"] == 88
    assert data["device_id"] == 1001


def test_health_camel_to_snake_mapping(monkeypatch):
    """Java 返回 healthScore（camelCase）应映射为 Python health_score（snake_case）。

    守护 main.py 第 36-38 行 `device.get("healthScore")` 提取逻辑：
    一旦 Java 侧改为 health_score，本测试会失败（KeyError 或 None）。
    """
    monkeypatch.setattr(
        "agent_maintenance.main.device_client.get_device",
        AsyncMock(
            return_value={
                "id": 2002,
                "healthScore": 42,
                "status": "MAINTENANCE",
                "deviceName": "回流焊",
            }
        ),
    )

    response = client.get("/maintenance/health/2002")

    assert response.status_code == 200
    data = response.json()
    # 核心断言：Java healthScore=42 → Python health_score=42
    assert data["health_score"] == 42
    assert data["risk_level"] == "HIGH"
