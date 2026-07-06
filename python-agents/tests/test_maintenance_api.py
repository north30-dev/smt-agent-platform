"""agent_maintenance.main FastAPI 接口集成测试。

使用 TestClient 调用真实路由，通过 monkeypatch 替换 main 模块中
device_client / diagnose / predict 的引用，不触达真实服务。

P0 B1：main 路由与被 mock 的函数均已改 async，TestClient 同步客户端内部自管事件循环，
测试函数保持 def，但 mock 必须用 AsyncMock 以匹配 await 语义。
"""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from agent_maintenance.device_client import DeviceServiceUnavailable
from agent_maintenance.main import app
from shared.llm_client import LLMClientError

client = TestClient(app)


def test_health_endpoint(monkeypatch):
    """健康评估接口应返回 200，healthScore=85 对应 risk_level=LOW。"""
    monkeypatch.setattr(
        "agent_maintenance.main.device_client.get_device",
        AsyncMock(
            return_value={
                "id": 1,
                "healthScore": 85,
                "status": "RUNNING",
                "deviceName": "贴片机",
            }
        ),
    )

    response = client.get("/v1/maintenance/health/1")

    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == 1
    assert data["health_score"] == 85
    assert data["status"] == "RUNNING"
    assert data["risk_level"] == "LOW"


def test_health_device_unavailable(monkeypatch):
    """device-service 不可达时应返回 503 与 ErrorResponse。"""
    monkeypatch.setattr(
        "agent_maintenance.main.device_client.get_device",
        AsyncMock(side_effect=DeviceServiceUnavailable("connection refused")),
    )

    response = client.get("/v1/maintenance/health/1")

    assert response.status_code == 503
    data = response.json()
    assert data["error"] == "device_service_unavailable"
    assert "connection refused" in data["message"]


def test_diagnose_endpoint(monkeypatch):
    """故障诊断接口应返回 200 与 DiagnoseResponse 结构。"""
    monkeypatch.setattr(
        "agent_maintenance.main.diagnose.diagnose",
        AsyncMock(
            return_value={
                "root_causes": ["x"],
                "repair_suggestions": ["y"],
                "similar_cases": [],
            }
        ),
    )

    response = client.post(
        "/v1/maintenance/diagnose", json={"device_id": 1, "symptom": "异响"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["root_causes"] == ["x"]
    assert data["repair_suggestions"] == ["y"]
    assert data["similar_cases"] == []


def test_predict_endpoint(monkeypatch):
    """预测性维护接口应返回 200 与 PredictResponse 结构。"""
    monkeypatch.setattr(
        "agent_maintenance.main.predict.predict",
        AsyncMock(
            return_value={
                "trend": "上升",
                "threshold_alerts": [],
                "forecast": None,
                "recommendation": "继续监控",
                "data_sufficient": True,
            }
        ),
    )

    response = client.get("/v1/maintenance/predict/1")

    assert response.status_code == 200
    data = response.json()
    assert data["trend"] == "上升"
    assert data["threshold_alerts"] == []
    assert data["forecast"] is None
    assert data["recommendation"] == "继续监控"
    assert data["data_sufficient"] is True


def test_cases_endpoint(monkeypatch):
    """案例录入接口应返回 200 与 case_id。"""
    monkeypatch.setattr(
        "agent_maintenance.main.diagnose.create_case",
        AsyncMock(return_value="case-1"),
    )

    response = client.post(
        "/v1/maintenance/cases",
        json={
            "device_type": "MOUNTER",
            "symptom": "x",
            "root_cause": "y",
            "solution": "z",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == "case-1"


def _patch_health(monkeypatch, health_score):
    """辅助：mock device_client.get_device 返回指定 healthScore。"""
    monkeypatch.setattr(
        "agent_maintenance.main.device_client.get_device",
        AsyncMock(
            return_value={
                "id": 1,
                "healthScore": health_score,
                "status": "RUNNING",
                "deviceName": "贴片机",
            }
        ),
    )


def test_health_score_100_returns_low(monkeypatch):
    """healthScore=100 应映射为 risk_level=LOW。补齐 phase2 B-6 盲区。"""
    _patch_health(monkeypatch, 100)

    response = client.get("/v1/maintenance/health/1")

    assert response.status_code == 200
    assert response.json()["risk_level"] == "LOW"


def test_health_score_60_returns_medium(monkeypatch):
    """healthScore=60 应映射为 risk_level=MEDIUM（边界值）。"""
    _patch_health(monkeypatch, 60)

    response = client.get("/v1/maintenance/health/1")

    assert response.status_code == 200
    assert response.json()["risk_level"] == "MEDIUM"


def test_health_score_30_returns_high(monkeypatch):
    """healthScore=30 应映射为 risk_level=HIGH。"""
    _patch_health(monkeypatch, 30)

    response = client.get("/v1/maintenance/health/1")

    assert response.status_code == 200
    assert response.json()["risk_level"] == "HIGH"


def test_health_score_missing_returns_503(monkeypatch):
    """healthScore 缺失（None）应抛 DeviceServiceUnavailable → 503。

    main.py 第 37-43 行：int(None) 抛 TypeError → raise DeviceServiceUnavailable。
    """
    monkeypatch.setattr(
        "agent_maintenance.main.device_client.get_device",
        AsyncMock(
            return_value={
                "id": 1,
                "healthScore": None,
                "status": "RUNNING",
                "deviceName": "贴片机",
            }
        ),
    )

    response = client.get("/v1/maintenance/health/1")

    assert response.status_code == 503
    data = response.json()
    assert data["error"] == "device_service_unavailable"


def test_diagnose_empty_symptom_returns_422():
    """diagnose 时 symptom 为空字符串应触发 Pydantic 校验失败 → 422。

    DiagnoseRequest.symptom 有 min_length=1 约束。
    """
    response = client.post(
        "/v1/maintenance/diagnose", json={"device_id": 1, "symptom": ""}
    )

    assert response.status_code == 422


def test_diagnose_llm_error_returns_503(monkeypatch):
    """diagnose 时 LLMClientError 应被异常处理器映射为 503。

    补齐 phase2 B-4 盲区：FastAPI 异常处理路径未测。
    """
    monkeypatch.setattr(
        "agent_maintenance.main.diagnose.diagnose",
        AsyncMock(side_effect=LLMClientError("LLM timeout")),
    )

    response = client.post(
        "/v1/maintenance/diagnose", json={"device_id": 1, "symptom": "异响"}
    )

    assert response.status_code == 503
    data = response.json()
    assert data["error"] == "llm_unavailable"
