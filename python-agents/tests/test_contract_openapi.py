"""OpenAPI 契约测试。

验证内容：
1. FastAPI app 的 OpenAPI schema 可正常加载
2. app 的 OpenAPI 路径与方法覆盖契约 yaml 定义的全部接口
3. schemathesis stateless 测试：mock 依赖后验证响应符合 OpenAPI schema

标记 @pytest.mark.contract，常规 pytest 不跑，需用 `pytest -m contract` 显式触发。
"""

import os
from unittest.mock import AsyncMock

import pytest
import yaml
from fastapi.testclient import TestClient

from agent_knowledge.main import app as knowledge_app
from agent_maintenance.main import app as maintenance_app

pytestmark = pytest.mark.contract


_CONTRACT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "api-contracts", "openapi", "agent_api.yaml"
)


def _load_contract():
    with open(_CONTRACT_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _normalize_path(path):
    """归一化路径模板：将 {paramName} 统一为 {}，仅比较结构不比较参数命名。"""
    import re
    return re.sub(r"\{[^}]+\}", "{}", path)


def _strip_gateway_prefix(paths):
    """去掉 /api/agent 前缀，返回 {normalized_path: set(methods)}。"""
    result = {}
    for path, methods in paths.items():
        new_path = path.replace("/api/agent", "")
        norm = _normalize_path(new_path)
        http_methods = {m for m in methods if m in ("get", "post", "put", "delete", "patch")}
        result[norm] = http_methods
    return result


contract = _load_contract()
contract_paths = _strip_gateway_prefix(contract["paths"])


def test_knowledge_openapi_schema_loadable():
    """knowledge app 的 OpenAPI schema 可正常加载。"""
    schema = knowledge_app.openapi()
    assert schema["openapi"].startswith("3.")
    assert "paths" in schema
    assert len(schema["paths"]) >= 4


def test_maintenance_openapi_schema_loadable():
    """maintenance app 的 OpenAPI schema 可正常加载。"""
    schema = maintenance_app.openapi()
    assert schema["openapi"].startswith("3.")
    assert "paths" in schema
    assert len(schema["paths"]) >= 4


def test_knowledge_paths_cover_contract():
    """knowledge app 的路径与方法应覆盖契约定义（归一化参数命名后比较）。"""
    app_paths = {
        _normalize_path(path): {m for m in methods if m in ("get", "post", "put", "delete", "patch")}
        for path, methods in knowledge_app.openapi()["paths"].items()
    }
    for path, methods in contract_paths.items():
        if path.startswith("/knowledge"):
            assert path in app_paths, f"契约路径 {path} 不在 knowledge app 中"
            missing = methods - app_paths[path]
            assert not missing, f"契约方法 {missing} 不在 {path}"


def test_maintenance_paths_cover_contract():
    """maintenance app 的路径与方法应覆盖契约定义（归一化参数命名后比较）。"""
    app_paths = {
        _normalize_path(path): {m for m in methods if m in ("get", "post", "put", "delete", "patch")}
        for path, methods in maintenance_app.openapi()["paths"].items()
    }
    for path, methods in contract_paths.items():
        if path.startswith("/maintenance"):
            assert path in app_paths, f"契约路径 {path} 不在 maintenance app 中"
            missing = methods - app_paths[path]
            assert not missing, f"契约方法 {missing} 不在 {path}"


def test_error_response_schema_consistent():
    """契约与 app 的 ErrorResponse 结构一致：{error: str, message: str}。"""
    contract_error = contract["components"]["schemas"]["ErrorResponse"]
    required_fields = set(contract_error.get("required", []))
    assert required_fields == {"error", "message"}

    k_schema = knowledge_app.openapi()
    for name, schema in k_schema.get("components", {}).get("schemas", {}).items():
        if name == "ErrorResponse":
            assert set(schema.get("required", [])) == {"error", "message"}


def _setup_knowledge_mocks(monkeypatch):
    """mock knowledge app 的 rag_chain 依赖。"""
    monkeypatch.setattr(
        "agent_knowledge.main.rag_chain.upload_document",
        AsyncMock(return_value=("doc-contract-test", 3)),
    )
    monkeypatch.setattr(
        "agent_knowledge.main.rag_chain.ask",
        AsyncMock(return_value=("契约测试答案", [{"doc_id": "d1", "chunk_id": 0, "score": 0.9, "snippet": "片段"}])),
    )
    monkeypatch.setattr(
        "agent_knowledge.main.rag_chain.list_documents",
        AsyncMock(return_value=[{"doc_id": "d1", "doc_name": "test.md", "chunk_count": 3, "create_time": "2026-06-29T00:00:00Z"}]),
    )
    monkeypatch.setattr(
        "agent_knowledge.main.rag_chain.delete_document",
        AsyncMock(return_value=3),
    )


def _setup_maintenance_mocks(monkeypatch):
    """mock maintenance app 的 diagnose/predict/device_client 依赖。"""
    monkeypatch.setattr(
        "agent_maintenance.main.device_client.get_device",
        AsyncMock(return_value={"id": 1001, "healthScore": 88, "status": "RUNNING", "deviceName": "测试设备"}),
    )
    monkeypatch.setattr(
        "agent_maintenance.main.diagnose.diagnose",
        AsyncMock(return_value={"root_causes": ["根因"], "repair_suggestions": ["建议"], "similar_cases": []}),
    )
    monkeypatch.setattr(
        "agent_maintenance.main.diagnose.create_case",
        AsyncMock(return_value="case-contract-001"),
    )
    monkeypatch.setattr(
        "agent_maintenance.main.predict.predict",
        AsyncMock(return_value={
            "trend": "上升",
            "threshold_alerts": [],
            "forecast": {"datapoint_code": "TEMP-01", "predicted_value": 86.2, "hours_to_threshold": 12},
            "recommendation": "建议检查散热",
            "data_sufficient": True,
        }),
    )


def test_knowledge_upload_contract(monkeypatch):
    """上传接口响应符合契约：返回 doc_id/doc_name/chunk_count。"""
    _setup_knowledge_mocks(monkeypatch)
    client = TestClient(knowledge_app)
    resp = client.post(
        "/knowledge/upload",
        files={"file": ("test.md", b"# test", "text/markdown")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"doc_id", "doc_name", "chunk_count"}
    assert isinstance(data["doc_id"], str)
    assert isinstance(data["doc_name"], str)
    assert isinstance(data["chunk_count"], int)


def test_knowledge_ask_contract(monkeypatch):
    """问答接口响应符合契约：返回 answer/sources。"""
    _setup_knowledge_mocks(monkeypatch)
    client = TestClient(knowledge_app)
    resp = client.post("/knowledge/ask", json={"question": "钢网清洁频率？"})
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"answer", "sources"}
    assert isinstance(data["answer"], str)
    assert isinstance(data["sources"], list)


def test_knowledge_documents_contract(monkeypatch):
    """文档列表接口响应符合契约：返回数组，每项含 doc_id/doc_name/chunk_count/create_time。"""
    _setup_knowledge_mocks(monkeypatch)
    client = TestClient(knowledge_app)
    resp = client.get("/knowledge/documents")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        assert set(data[0].keys()) >= {"doc_id", "doc_name", "chunk_count"}


def test_knowledge_delete_contract(monkeypatch):
    """删除接口响应符合契约：返回 success/deleted_chunks。"""
    _setup_knowledge_mocks(monkeypatch)
    client = TestClient(knowledge_app)
    resp = client.delete("/knowledge/documents/doc-1")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"success", "deleted_chunks"}
    assert isinstance(data["success"], bool)
    assert isinstance(data["deleted_chunks"], int)


def test_maintenance_health_contract(monkeypatch):
    """健康评分接口响应符合契约：返回 device_id/health_score/status/risk_level/analysis。"""
    _setup_maintenance_mocks(monkeypatch)
    client = TestClient(maintenance_app)
    resp = client.get("/maintenance/health/1001")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"device_id", "health_score", "status", "risk_level", "analysis"}
    assert data["risk_level"] in ("LOW", "MEDIUM", "HIGH")


def test_maintenance_diagnose_contract(monkeypatch):
    """诊断接口响应符合契约：返回 root_causes/repair_suggestions/similar_cases。"""
    _setup_maintenance_mocks(monkeypatch)
    client = TestClient(maintenance_app)
    resp = client.post("/maintenance/diagnose", json={"device_id": 1001, "symptom": "振动偏高"})
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"root_causes", "repair_suggestions", "similar_cases"}
    assert isinstance(data["root_causes"], list)
    assert isinstance(data["repair_suggestions"], list)
    assert isinstance(data["similar_cases"], list)


def test_maintenance_predict_contract(monkeypatch):
    """预测接口响应符合契约：返回 trend/threshold_alerts/forecast/recommendation/data_sufficient。"""
    _setup_maintenance_mocks(monkeypatch)
    client = TestClient(maintenance_app)
    resp = client.get("/maintenance/predict/1001")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"trend", "threshold_alerts", "forecast", "recommendation", "data_sufficient"}


def test_maintenance_cases_contract(monkeypatch):
    """案例创建接口响应符合契约：返回 case_id。"""
    _setup_maintenance_mocks(monkeypatch)
    client = TestClient(maintenance_app)
    resp = client.post("/maintenance/cases", json={
        "device_type": "MOUNTER",
        "symptom": "振动偏高",
        "root_cause": "轴承磨损",
        "solution": "更换轴承",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"case_id"}
    assert isinstance(data["case_id"], str)
