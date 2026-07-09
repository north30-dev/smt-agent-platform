"""agent_orchestrator.main FastAPI 接口集成测试。

使用 TestClient 调用真实路由，通过 monkeypatch 替换 main 模块中
app_graph 的 ainvoke 调用与 nodes 层 agent_clients / llm_client，
不触达真实服务。
"""

import pytest
from fastapi.testclient import TestClient

from agent_orchestrator import main as orchestrator_main

# raise_server_exceptions=False：允许测试 500 异常处理器的响应体
# （默认 True 会把服务端异常原样抛出，无法断言返回的 ErrorResponse）
client = TestClient(orchestrator_main.app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def workflow_store(monkeypatch):
    """用内存 dict 替换 shared.db 的工作流持久化，避免触达真实 PG（autouse）。

    REL-1 迁移后 orchestrator 通过 shared.db.save_workflow/get_workflow 持久化，
    测试需 mock 这两个模块级符号；返回 store 供断言使用。
    """
    store: dict[str, dict] = {}

    async def _fake_save(workflow_id: str, status: str, data: dict) -> None:
        store[workflow_id] = {"workflow_id": workflow_id, "status": status, **data}

    async def _fake_get(workflow_id: str):
        return store.get(workflow_id)

    monkeypatch.setattr(orchestrator_main, "save_workflow", _fake_save)
    monkeypatch.setattr(orchestrator_main, "_get_workflow", _fake_get)
    yield store


def _patch_graph_success(monkeypatch, summary_text="LLM 摘要"):
    """mock app_graph.ainvoke 返回全成功结果（含 execution 指令）。"""
    async def _fake_ainvoke(initial_state):
        return {
            "device_id": initial_state["device_id"],
            "symptom": initial_state["symptom"],
            "diagnosis": {"root_causes": ["x"]},
            "quality_assessment": {"root_causes": ["y"]},
            "schedule_adjustment": {"estimated_delay_hours": 1.0},
            "instructions": [
                {"instruction_id": "INST-1", "type": "REPAIR", "priority": "MEDIUM"}
            ],
            "summary": summary_text,
            "errors": {},
        }
    monkeypatch.setattr(orchestrator_main.app_graph, "ainvoke", _fake_ainvoke)


# ---------------------------------------------------------------------------
# /healthz
# ---------------------------------------------------------------------------


def test_healthz_returns_200():
    """/healthz 应返回 200 与 healthy 状态。"""
    response = client.get("/healthz")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


# ---------------------------------------------------------------------------
# POST /v1/orchestrator/device_fault
# ---------------------------------------------------------------------------


def test_device_fault_returns_200_with_all_fields(monkeypatch):
    """成功：返回 200，包含 workflow_id 与全部结果字段（含 instructions）。"""
    _patch_graph_success(monkeypatch, summary_text="汇总")

    response = client.post(
        "/v1/orchestrator/device_fault",
        json={"device_id": 1, "symptom": "异响"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["workflow_id"].startswith("wf-")
    assert data["status"] == "SUCCESS"
    assert data["diagnosis"] == {"root_causes": ["x"]}
    assert data["quality_assessment"] == {"root_causes": ["y"]}
    assert data["schedule_adjustment"] == {"estimated_delay_hours": 1.0}
    assert data["instructions"] == [
        {"instruction_id": "INST-1", "type": "REPAIR", "priority": "MEDIUM"}
    ]
    assert data["summary"] == "汇总"
    assert data["errors"] == {}


def test_device_fault_partial_status(monkeypatch):
    """部分节点失败 → status=PARTIAL。"""
    async def _fake_ainvoke(initial_state):
        return {
            "device_id": initial_state["device_id"],
            "symptom": initial_state["symptom"],
            "diagnosis": None,
            "quality_assessment": {"status": "skipped", "reason": "down"},
            "schedule_adjustment": {"estimated_delay_hours": 1.0},
            "summary": "部分摘要",
            "errors": {"quality": "down"},
        }
    monkeypatch.setattr(orchestrator_main.app_graph, "ainvoke", _fake_ainvoke)

    response = client.post(
        "/v1/orchestrator/device_fault",
        json={"device_id": 2, "symptom": "温度异常"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PARTIAL"
    assert data["diagnosis"] is None
    assert data["errors"] == {"quality": "down"}


def test_device_fault_failed_status(monkeypatch):
    """全部节点失败 → status=FAILED。"""
    async def _fake_ainvoke(initial_state):
        return {
            "device_id": initial_state["device_id"],
            "symptom": initial_state["symptom"],
            "diagnosis": None,
            "quality_assessment": {"status": "skipped", "reason": "down"},
            "schedule_adjustment": {"status": "skipped", "reason": "down"},
            "summary": "全部失败摘要",
            "errors": {
                "maintenance": "down",
                "quality": "down",
                "scheduler": "down",
            },
        }
    monkeypatch.setattr(orchestrator_main.app_graph, "ainvoke", _fake_ainvoke)

    response = client.post(
        "/v1/orchestrator/device_fault",
        json={"device_id": 3, "symptom": "停机"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "FAILED"


def test_device_fault_invalid_device_id_returns_422():
    """device_id=0 应触发 Pydantic ge=1 校验失败 → 422。"""
    response = client.post(
        "/v1/orchestrator/device_fault",
        json={"device_id": 0, "symptom": "异响"},
    )

    assert response.status_code == 422


def test_device_fault_empty_symptom_returns_422():
    """symptom 为空应触发 min_length=1 校验失败 → 422。"""
    response = client.post(
        "/v1/orchestrator/device_fault",
        json={"device_id": 1, "symptom": ""},
    )

    assert response.status_code == 422


def test_device_fault_persists_workflow(monkeypatch, workflow_store):
    """POST 后应通过 save_workflow 持久化，可供 GET 查询。"""
    _patch_graph_success(monkeypatch)

    response = client.post(
        "/v1/orchestrator/device_fault",
        json={"device_id": 1, "symptom": "异响"},
    )

    workflow_id = response.json()["workflow_id"]
    assert workflow_id in workflow_store
    assert workflow_store[workflow_id]["status"] == "SUCCESS"


# ---------------------------------------------------------------------------
# POST /v1/orchestrator/device_fault_event
# ---------------------------------------------------------------------------


def test_device_fault_event_returns_200_with_instructions(monkeypatch):
    """事件入口成功：返回 WorkflowResponse，包含 instructions 字段。"""
    _patch_graph_success(monkeypatch, summary_text="事件汇总")

    response = client.post(
        "/v1/orchestrator/device_fault_event",
        json={"device_id": 9, "symptom": "温度异常", "source": "kafka"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["workflow_id"].startswith("wf-")
    assert data["status"] == "SUCCESS"
    assert data["diagnosis"] == {"root_causes": ["x"]}
    assert data["instructions"] == [
        {"instruction_id": "INST-1", "type": "REPAIR", "priority": "MEDIUM"}
    ]
    assert data["summary"] == "事件汇总"
    assert data["errors"] == {}


def test_device_fault_event_source_defaults_to_kafka(monkeypatch):
    """source 缺省时默认为 kafka，编排逻辑与 device_fault 一致。"""
    _patch_graph_success(monkeypatch)

    response = client.post(
        "/v1/orchestrator/device_fault_event",
        json={"device_id": 10, "symptom": "停机"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["instructions"] == [
        {"instruction_id": "INST-1", "type": "REPAIR", "priority": "MEDIUM"}
    ]


def test_device_fault_event_persists_workflow(monkeypatch, workflow_store):
    """事件入口也应通过 save_workflow 持久化，可供 GET 查询。"""
    _patch_graph_success(monkeypatch)

    response = client.post(
        "/v1/orchestrator/device_fault_event",
        json={"device_id": 11, "symptom": "故障", "source": "kafka"},
    )

    workflow_id = response.json()["workflow_id"]
    assert workflow_id in workflow_store
    assert workflow_store[workflow_id]["status"] == "SUCCESS"
    # instructions 应持久化
    assert workflow_store[workflow_id]["instructions"] == [
        {"instruction_id": "INST-1", "type": "REPAIR", "priority": "MEDIUM"}
    ]


def test_device_fault_event_invalid_device_id_returns_422():
    """device_fault_event: device_id=0 → 422。"""
    response = client.post(
        "/v1/orchestrator/device_fault_event",
        json={"device_id": 0, "symptom": "异响", "source": "kafka"},
    )

    assert response.status_code == 422


def test_device_fault_event_empty_symptom_returns_422():
    """device_fault_event: symptom 为空 → 422。"""
    response = client.post(
        "/v1/orchestrator/device_fault_event",
        json={"device_id": 1, "symptom": "", "source": "kafka"},
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /v1/orchestrator/workflows/{workflow_id}
# ---------------------------------------------------------------------------


def test_get_workflow_returns_stored(monkeypatch):
    """GET 已存在 workflow_id → 返回 200 与存储的结果。"""
    _patch_graph_success(monkeypatch, summary_text="已存储摘要")

    post_resp = client.post(
        "/v1/orchestrator/device_fault",
        json={"device_id": 5, "symptom": "故障"},
    )
    workflow_id = post_resp.json()["workflow_id"]

    response = client.get(f"/v1/orchestrator/workflows/{workflow_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["workflow_id"] == workflow_id
    assert data["status"] == "SUCCESS"
    assert data["summary"] == "已存储摘要"
    # instructions 通过 JSONB 持久化后应能正确回读
    assert data["instructions"] == [
        {"instruction_id": "INST-1", "type": "REPAIR", "priority": "MEDIUM"}
    ]


def test_get_workflow_unknown_returns_404():
    """GET 不存在的 workflow_id → 404 + ErrorResponse。"""
    response = client.get("/v1/orchestrator/workflows/wf-unknown")

    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "workflow_not_found"
    assert "wf-unknown" in data["message"]


# ---------------------------------------------------------------------------
# 异常处理兜底
# ---------------------------------------------------------------------------


def test_device_fault_internal_error_returns_500(monkeypatch):
    """graph.ainvoke 抛出未预期异常 → 500 + ErrorResponse。"""
    async def _explode(_):
        raise RuntimeError("unexpected")
    monkeypatch.setattr(orchestrator_main.app_graph, "ainvoke", _explode)

    response = client.post(
        "/v1/orchestrator/device_fault",
        json={"device_id": 1, "symptom": "x"},
    )

    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "internal_error"


def test_device_fault_workflow_id_uniqueness(monkeypatch):
    """连续两次 POST 应生成不同的 workflow_id。"""
    _patch_graph_success(monkeypatch)

    r1 = client.post(
        "/v1/orchestrator/device_fault",
        json={"device_id": 1, "symptom": "a"},
    )
    r2 = client.post(
        "/v1/orchestrator/device_fault",
        json={"device_id": 1, "symptom": "a"},
    )

    assert r1.json()["workflow_id"] != r2.json()["workflow_id"]


# ---------------------------------------------------------------------------
# 多工作流持久化（REL-1 迁移后无内存上限）
# ---------------------------------------------------------------------------


def test_multiple_workflows_persist(monkeypatch, workflow_store):
    """101 条工作流均可正常存储（验证 PG 迁移后无内存上限副作用）。"""
    _patch_graph_success(monkeypatch)

    ids = []
    for i in range(101):
        r = client.post(
            "/v1/orchestrator/device_fault",
            json={"device_id": i + 1, "symptom": f"s{i}"},
        )
        ids.append(r.json()["workflow_id"])

    assert len(workflow_store) == 101
    for wid in (ids[0], ids[50], ids[100]):
        assert wid in workflow_store
        assert workflow_store[wid]["status"] == "SUCCESS"
