"""agent_quality.main FastAPI 接口集成测试。

使用 TestClient 调用真实路由，通过 monkeypatch 替换 main 模块中
monitor / root_cause / alert_store 的引用，不触达真实服务。

TestClient 同步客户端内部自管事件循环，测试函数保持 def，
但 mock 必须用 AsyncMock 以匹配 await 语义。
"""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from agent_quality import alert_store
from agent_quality.device_client import DeviceServiceUnavailable
from agent_quality.main import app
from shared.llm_client import LLMClientError
from shared.vector_store import VectorStoreError

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_alert_pool():
    """每个用例前后重置 alert_store 模块级连接池，避免跨用例污染。"""
    alert_store._pool = None
    yield
    alert_store._pool = None


def test_healthz():
    """/healthz 应返回 200 与 healthy 状态。"""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["uptime_seconds"] >= 0
    assert isinstance(data["checks"], list)


def test_monitor_endpoint_ok(monkeypatch):
    """monitor 接口 status=OK 时应返回 200 与 MonitorResponse 结构。"""
    monkeypatch.setattr(
        "agent_quality.main.monitor.monitor",
        AsyncMock(
            return_value={
                "device_id": 1,
                "defect_rate": 0.005,
                "threshold": 0.02,
                "status": "OK",
                "datapoints": [
                    {
                        "datapoint_code": "AOI_DEFECT_RATE",
                        "value": 0.005,
                        "timestamp": "2026-07-06T00:00:00Z",
                    }
                ],
                "analyzed_at": "2026-07-06T00:00:00Z",
            }
        ),
    )

    response = client.get("/v1/quality/monitor/1")

    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == 1
    assert data["status"] == "OK"
    assert data["defect_rate"] == 0.005
    assert data["threshold"] == 0.02
    assert len(data["datapoints"]) == 1
    assert data["datapoints"][0]["datapoint_code"] == "AOI_DEFECT_RATE"
    assert data["analyzed_at"] == "2026-07-06T00:00:00Z"


def test_monitor_endpoint_alert(monkeypatch):
    """monitor 接口 status=ALERT 时应返回 200 + ALERT 状态。"""
    monkeypatch.setattr(
        "agent_quality.main.monitor.monitor",
        AsyncMock(
            return_value={
                "device_id": 1,
                "defect_rate": 0.05,
                "threshold": 0.02,
                "status": "ALERT",
                "datapoints": [],
                "analyzed_at": "2026-07-06T00:00:00Z",
            }
        ),
    )

    response = client.get("/v1/quality/monitor/1")

    assert response.status_code == 200
    assert response.json()["status"] == "ALERT"


def test_monitor_endpoint_insufficient_data(monkeypatch):
    """monitor 接口数据不足时应返回 INSUFFICIENT_DATA。"""
    monkeypatch.setattr(
        "agent_quality.main.monitor.monitor",
        AsyncMock(
            return_value={
                "device_id": 1,
                "defect_rate": 0.0,
                "threshold": 0.02,
                "status": "INSUFFICIENT_DATA",
                "datapoints": [],
                "analyzed_at": "2026-07-06T00:00:00Z",
            }
        ),
    )

    response = client.get("/v1/quality/monitor/1")

    assert response.status_code == 200
    assert response.json()["status"] == "INSUFFICIENT_DATA"


def test_monitor_device_unavailable_returns_503(monkeypatch):
    """monitor 接口 device-service 不可达时应返回 503。"""
    monkeypatch.setattr(
        "agent_quality.main.monitor.monitor",
        AsyncMock(side_effect=DeviceServiceUnavailable("connection refused")),
    )

    response = client.get("/v1/quality/monitor/1")

    assert response.status_code == 503
    data = response.json()
    assert data["error"] == "device_service_unavailable"
    assert "connection refused" in data["message"]


def test_root_cause_endpoint(monkeypatch):
    """root_cause 接口应返回 200 与 RootCauseResponse 结构。"""
    monkeypatch.setattr(
        "agent_quality.main.root_cause.analyze",
        AsyncMock(
            return_value={
                "device_id": 1,
                "root_causes": [{"category": "机", "cause": "炉温偏移"}],
                "corrective_actions": ["调整温区"],
                "similar_cases": [
                    {
                        "case_id": "q1",
                        "description": "立碑",
                        "root_cause": "炉温偏移",
                        "corrective_action": "调整温区",
                        "score": 0.9,
                    }
                ],
            }
        ),
    )

    response = client.post(
        "/v1/quality/root_cause",
        json={"device_id": 1, "defect_description": "元器件立碑"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == 1
    assert len(data["root_causes"]) == 1
    assert data["root_causes"][0]["category"] == "机"
    assert data["root_causes"][0]["cause"] == "炉温偏移"
    assert data["corrective_actions"] == ["调整温区"]
    assert len(data["similar_cases"]) == 1
    assert data["similar_cases"][0]["case_id"] == "q1"


def test_root_cause_invalid_body_returns_422():
    """root_cause 缺字段应触发 Pydantic 校验失败 → 422。"""
    response = client.post("/v1/quality/root_cause", json={"device_id": 1})
    assert response.status_code == 422


def test_root_cause_invalid_device_id_returns_422():
    """device_id=0 不满足 ge=1 约束应返回 422。"""
    response = client.post(
        "/v1/quality/root_cause",
        json={"device_id": 0, "defect_description": "x"},
    )
    assert response.status_code == 422


def test_root_cause_llm_error_returns_503(monkeypatch):
    """root_cause 时 LLMClientError 应映射为 503。"""
    monkeypatch.setattr(
        "agent_quality.main.root_cause.analyze",
        AsyncMock(side_effect=LLMClientError("LLM timeout")),
    )

    response = client.post(
        "/v1/quality/root_cause",
        json={"device_id": 1, "defect_description": "立碑"},
    )

    assert response.status_code == 503
    assert response.json()["error"] == "llm_unavailable"


def test_root_cause_vector_store_error_returns_503(monkeypatch):
    """root_cause 时 VectorStoreError 应映射为 503。"""
    monkeypatch.setattr(
        "agent_quality.main.root_cause.analyze",
        AsyncMock(side_effect=VectorStoreError("Milvus down")),
    )

    response = client.post(
        "/v1/quality/root_cause",
        json={"device_id": 1, "defect_description": "立碑"},
    )

    assert response.status_code == 503
    assert response.json()["error"] == "vector_store_unavailable"


def test_cases_endpoint(monkeypatch):
    """cases 录入接口应返回 200 与 case_id。"""
    monkeypatch.setattr(
        "agent_quality.main.root_cause.create_case",
        AsyncMock(return_value="qcase-abc12345"),
    )

    response = client.post(
        "/v1/quality/cases",
        json={
            "defect_type": "AOI_TOMBSTONE",
            "description": "立碑",
            "root_cause": "炉温偏移",
            "corrective_action": "调整温区",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == "qcase-abc12345"


def test_cases_invalid_body_returns_422():
    """cases 缺字段应触发 422。"""
    response = client.post(
        "/v1/quality/cases",
        json={"defect_type": "X"},
    )
    assert response.status_code == 422


def test_cases_empty_defect_type_returns_422():
    """defect_type 为空字符串应触发 min_length=1 约束 → 422。"""
    response = client.post(
        "/v1/quality/cases",
        json={
            "defect_type": "",
            "description": "x",
            "root_cause": "y",
            "corrective_action": "z",
        },
    )
    assert response.status_code == 422


def test_alerts_endpoint(monkeypatch):
    """alerts 接口应返回 200 与 AlertsPageResponse 结构。"""
    monkeypatch.setattr(
        "agent_quality.main.alert_store.list_alerts",
        AsyncMock(
            return_value={
                "records": [
                    {
                        "id": 1,
                        "device_id": 1,
                        "defect_rate": 0.05,
                        "threshold": 0.02,
                        "status": "ALERT",
                        "datapoint_code": "AOI_DEFECT_RATE",
                        "alert_time": "2026-07-06T00:00:00+00:00",
                    }
                ],
                "total": 1,
                "page": 1,
                "size": 20,
            }
        ),
    )

    response = client.get("/v1/quality/alerts")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["page"] == 1
    assert data["size"] == 20
    assert len(data["records"]) == 1
    assert data["records"][0]["id"] == 1
    assert data["records"][0]["device_id"] == 1
    assert data["records"][0]["status"] == "ALERT"
    assert data["records"][0]["datapoint_code"] == "AOI_DEFECT_RATE"


def test_alerts_with_pagination(monkeypatch):
    """alerts 接口支持 page/size 查询参数。"""
    monkeypatch.setattr(
        "agent_quality.main.alert_store.list_alerts",
        AsyncMock(
            return_value={
                "records": [],
                "total": 50,
                "page": 3,
                "size": 10,
            }
        ),
    )

    response = client.get("/v1/quality/alerts?page=3&size=10")

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 3
    assert data["size"] == 10
    assert data["total"] == 50
    assert data["records"] == []


def test_alerts_propagates_args(monkeypatch):
    """alerts 接口应将 page/size 参数透传给 alert_store.list_alerts。"""
    list_alerts_mock = AsyncMock(
        return_value={"records": [], "total": 0, "page": 2, "size": 5}
    )
    monkeypatch.setattr(
        "agent_quality.main.alert_store.list_alerts", list_alerts_mock
    )

    response = client.get("/v1/quality/alerts?page=2&size=5")

    assert response.status_code == 200
    list_alerts_mock.assert_called_once_with(2, 5)


def test_alerts_default_args(monkeypatch):
    """alerts 接口默认应传 page=1、size=None（由 alert_store 内部取默认值）。"""
    list_alerts_mock = AsyncMock(
        return_value={"records": [], "total": 0, "page": 1, "size": 20}
    )
    monkeypatch.setattr(
        "agent_quality.main.alert_store.list_alerts", list_alerts_mock
    )

    response = client.get("/v1/quality/alerts")

    assert response.status_code == 200
    list_alerts_mock.assert_called_once_with(1, None)
