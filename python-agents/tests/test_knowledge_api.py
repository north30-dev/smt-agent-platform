"""agent-knowledge.main FastAPI 接口集成测试。

使用 TestClient 调用真实路由，通过 monkeypatch 替换 main 模块中
rag_chain 引用的方法，不触达真实 Milvus 与大模型。

P0 B1：main 路由与 rag_chain 方法均已改 async，TestClient 同步客户端内部自管事件循环，
测试函数保持 def，但 mock 必须用 AsyncMock 以匹配 await 语义。
"""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from agent_knowledge.main import app
from shared.llm_client import LLMClientError
from shared.vector_store import VectorStoreError

client = TestClient(app)


def test_upload_endpoint(monkeypatch):
    """上传接口应返回 200 与 UploadResponse 结构。"""
    monkeypatch.setattr(
        "agent_knowledge.main.rag_chain.upload_document",
        AsyncMock(return_value=("doc-1", 5)),
    )

    response = client.post(
        "/v1/knowledge/upload",
        files={"file": ("manual.txt", b"hello world", "text/plain")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["doc_id"] == "doc-1"
    assert data["doc_name"] == "manual.txt"
    assert data["chunk_count"] == 5


def test_ask_endpoint(monkeypatch):
    """问答接口应返回 200 与 AskResponse 结构，sources 字段透传。"""
    monkeypatch.setattr(
        "agent_knowledge.main.rag_chain.ask",
        AsyncMock(
            return_value=(
                "答案",
                [{"doc_id": "d1", "chunk_id": 0, "score": 0.9, "snippet": "片段"}],
            )
        ),
    )

    response = client.post("/v1/knowledge/ask", json={"question": "钢网清洁频率？"})

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "答案"
    assert data["sources"] == [
        {"doc_id": "d1", "chunk_id": 0, "score": 0.9, "snippet": "片段"}
    ]


def test_ask_invalid():
    """空 body 应触发 Pydantic 校验失败 → 422。"""
    response = client.post("/v1/knowledge/ask", json={})

    assert response.status_code == 422


def test_documents_endpoint(monkeypatch):
    """文档列表接口应返回 200 与 DocumentInfo 列表。"""
    monkeypatch.setattr(
        "agent_knowledge.main.rag_chain.list_documents",
        AsyncMock(
            return_value=[
                {
                    "doc_id": "d1",
                    "doc_name": "a.pdf",
                    "chunk_count": 3,
                    "create_time": "2026-06-27T08:30:00Z",
                }
            ]
        ),
    )

    response = client.get("/v1/knowledge/documents")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["doc_id"] == "d1"
    assert data[0]["doc_name"] == "a.pdf"
    assert data[0]["chunk_count"] == 3


def test_delete_endpoint(monkeypatch):
    """删除接口应返回 200 与 DeleteResponse 结构。"""
    monkeypatch.setattr(
        "agent_knowledge.main.rag_chain.delete_document",
        AsyncMock(return_value=3),
    )

    response = client.delete("/v1/knowledge/documents/doc-1")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["deleted_chunks"] == 3


def test_ask_llm_unavailable_returns_503(monkeypatch):
    """ask 时 LLMClientError 应被异常处理器映射为 503 + ErrorResponse。

    补齐 phase2 报告 B-4 盲区：FastAPI 异常处理路径未测。
    """
    monkeypatch.setattr(
        "agent_knowledge.main.rag_chain.ask",
        AsyncMock(side_effect=LLMClientError("LLM timeout")),
    )

    response = client.post("/v1/knowledge/ask", json={"question": "钢网清洁？"})

    assert response.status_code == 503
    data = response.json()
    assert data["error"] == "LLM_UNAVAILABLE"
    assert "LLM timeout" in data["message"]


def test_ask_vector_store_error_returns_503(monkeypatch):
    """ask 时 VectorStoreError 应被异常处理器映射为 503 + ErrorResponse。"""
    monkeypatch.setattr(
        "agent_knowledge.main.rag_chain.ask",
        AsyncMock(side_effect=VectorStoreError("Milvus down")),
    )

    response = client.post("/v1/knowledge/ask", json={"question": "钢网清洁？"})

    assert response.status_code == 503
    data = response.json()
    assert data["error"] == "VECTOR_STORE_UNAVAILABLE"
    assert "Milvus down" in data["message"]


def test_upload_empty_file_returns_400():
    """上传空文件应返回 400 + ErrorResponse。

    不需要 mock：main.py upload 接口直接检查 content 为空。
    """
    response = client.post(
        "/v1/knowledge/upload",
        files={"file": ("empty.txt", b"", "text/plain")},
    )

    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "INVALID_FILE"
    assert data["message"] == "上传文件不能为空"
