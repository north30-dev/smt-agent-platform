"""agent-knowledge.main FastAPI 接口集成测试。

使用 TestClient 调用真实路由，通过 monkeypatch 替换 main 模块中
rag_chain 引用的方法，不触达真实 Milvus 与大模型。
"""

from fastapi.testclient import TestClient

from agent_knowledge.main import app

client = TestClient(app)


def test_upload_endpoint(monkeypatch):
    """上传接口应返回 200 与 UploadResponse 结构。"""
    monkeypatch.setattr(
        "agent_knowledge.main.rag_chain.upload_document",
        lambda content, filename: ("doc-1", 5),
    )

    response = client.post(
        "/knowledge/upload",
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
        lambda question, top_k=5: (
            "答案",
            [{"doc_id": "d1", "chunk_id": 0, "score": 0.9, "snippet": "片段"}],
        ),
    )

    response = client.post("/knowledge/ask", json={"question": "钢网清洁频率？"})

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "答案"
    assert data["sources"] == [
        {"doc_id": "d1", "chunk_id": 0, "score": 0.9, "snippet": "片段"}
    ]


def test_ask_invalid():
    """空 body 应触发 Pydantic 校验失败 → 422。"""
    response = client.post("/knowledge/ask", json={})

    assert response.status_code == 422


def test_documents_endpoint(monkeypatch):
    """文档列表接口应返回 200 与 DocumentInfo 列表。"""
    monkeypatch.setattr(
        "agent_knowledge.main.rag_chain.list_documents",
        lambda: [
            {
                "doc_id": "d1",
                "doc_name": "a.pdf",
                "chunk_count": 3,
                "create_time": "2026-06-27T08:30:00Z",
            }
        ],
    )

    response = client.get("/knowledge/documents")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["doc_id"] == "d1"
    assert data[0]["doc_name"] == "a.pdf"
    assert data[0]["chunk_count"] == 3


def test_delete_endpoint(monkeypatch):
    """删除接口应返回 200 与 DeleteResponse 结构。"""
    monkeypatch.setattr(
        "agent_knowledge.main.rag_chain.delete_document", lambda doc_id: 3
    )

    response = client.delete("/knowledge/documents/doc-1")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["deleted_chunks"] == 3
