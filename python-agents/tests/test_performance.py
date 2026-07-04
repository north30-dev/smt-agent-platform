"""性能基准测试（PRD §4.4 P0 指标验证）。

补齐 phase2 报告 RAG-性能验证盲区：PRD §4.4 P0 要求 RAG 检索响应 <3s，此前零验证。

标记 slow，常规 pytest 不跑，需用 `pytest -m slow` 显式触发。
mock llm_client 与 vector_store 为即时响应，测量 FastAPI 路由 + RAG 管道开销
（不含真实 LLM/Milvus 网络延迟），用于验证：
1. 端到端 RAG 响应 <3s（PRD P0 红线）
2. LLM 单次调用无阻塞（验证 Batch 1 异步改造未引入同步阻塞）
"""

import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from agent_knowledge.main import app
from shared import llm_client, vector_store

pytestmark = pytest.mark.slow


def _patch_rag_dependencies(monkeypatch):
    """mock rag_chain.ask 的四个底层依赖为即时响应。

    rag_chain.ask 调用链（rag_chain.py L78-98）：
        vector_store.count → llm_client.embed → vector_store.search → llm_client.chat
    - vector_store.count/search 是同步函数，rag_chain 通过 asyncio.to_thread 包装后 await，
      故 mock 为 MagicMock（同步返回），不能是 AsyncMock
    - llm_client.embed/chat 本身是 async，mock 为 AsyncMock
    全部即时返回，避免真实网络 IO，仅测量管道开销。
    """
    monkeypatch.setattr(
        vector_store,
        "count",
        MagicMock(return_value=10),
    )
    monkeypatch.setattr(
        llm_client,
        "embed",
        AsyncMock(return_value=[[0.1] * 128]),
    )
    monkeypatch.setattr(
        vector_store,
        "search",
        MagicMock(return_value=[
            {"doc_id": "d1", "chunk_id": 0, "score": 0.95, "content": "钢网清洁每班次一次"}
        ]),
    )
    monkeypatch.setattr(
        llm_client,
        "chat",
        AsyncMock(return_value="钢网清洁频率为每班次一次。"),
    )


def test_rag_end_to_end_under_3_seconds(monkeypatch):
    """PRD §4.4 P0：RAG 检索响应 <3s。

    mock 四个依赖为即时响应后，通过 TestClient 调 /v1/knowledge/ask 端点，
    断言端到端延迟 <3.0s。3s 是 PRD 红线，包含：
    - FastAPI 路由分发
    - rag_chain.ask 管道编排（asyncio.to_thread 包装同步调用）
    - Pydantic 响应模型序列化
    - mock 调用开销（应可忽略）
    """
    _patch_rag_dependencies(monkeypatch)
    client = TestClient(app)

    start = time.perf_counter()
    resp = client.post("/v1/knowledge/ask", json={"question": "钢网清洁频率是多少？"})
    elapsed = time.perf_counter() - start

    assert resp.status_code == 200, f"响应失败: {resp.text}"
    data = resp.json()
    assert "answer" in data
    assert "sources" in data
    assert elapsed < 3.0, (
        f"RAG 端到端延迟 {elapsed:.3f}s 超过 PRD §4.4 P0 红线 3.0s"
    )


def test_llm_chat_latency_baseline(monkeypatch):
    """LLM 单次调用延迟基准（mock，验证无阻塞）。

    Batch 1 已将 llm_client.chat 改为 async + 共享 AsyncClient + tenacity 重试。
    本测试 mock chat 为即时响应，断言调用返回延迟 <0.5s，
    用于验证未引入同步阻塞（如 time.sleep、同步 IO 残留）。
    """
    monkeypatch.setattr(
        llm_client,
        "chat",
        AsyncMock(return_value="即时回答"),
    )
    client = TestClient(app)
    # mock vector_store 让 ask 走完整链路但不触达真实 Milvus
    # count/search 是同步函数（rag_chain 通过 asyncio.to_thread 包装），用 MagicMock
    monkeypatch.setattr(vector_store, "count", MagicMock(return_value=1))
    monkeypatch.setattr(
        llm_client,
        "embed",
        AsyncMock(return_value=[[0.1] * 128]),
    )
    monkeypatch.setattr(
        vector_store,
        "search",
        MagicMock(return_value=[{"doc_id": "d1", "chunk_id": 0, "score": 0.9, "content": "ctx"}]),
    )

    start = time.perf_counter()
    resp = client.post("/v1/knowledge/ask", json={"question": "test"})
    elapsed = time.perf_counter() - start

    assert resp.status_code == 200
    assert elapsed < 0.5, (
        f"LLM 调用延迟 {elapsed:.3f}s 超过基准 0.5s，可能存在同步阻塞"
    )
