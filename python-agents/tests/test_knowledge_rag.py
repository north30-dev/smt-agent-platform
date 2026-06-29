"""agent-knowledge.rag_chain 单元测试。

使用 monkeypatch 替换 rag_chain 模块内已 import 的 shared 引用
（llm_client / vector_store / doc_meta_store）与 document_loader.load_and_split，
不依赖真实 Milvus、大模型服务与 PostgreSQL。

P0 B1+P0-5：rag_chain 全接口已改 async，元数据已迁移到 doc_meta_store（PG）。
- llm_client.embed/chat → AsyncMock（被 await 调用）
- doc_meta_store.save_doc_meta → AsyncMock（被 await 调用）
- vector_store.count/search/insert/init_collections → MagicMock（被 asyncio.to_thread 包装为同步）
- load_and_split → 同步 lambda（被 asyncio.to_thread 包装）
"""

from unittest.mock import AsyncMock, MagicMock

from agent_knowledge.rag_chain import COLLECTION, ask, upload_document


async def test_ask_empty_knowledge(monkeypatch):
    """空知识库（count==0）应直接返回兜底文案与空来源。"""
    mock_vs = MagicMock()
    mock_vs.count.return_value = 0
    monkeypatch.setattr("agent_knowledge.rag_chain.vector_store", mock_vs)

    answer, sources = await ask("钢网清洁频率是多少？")

    assert answer == "知识库为空，请先上传文档。"
    assert sources == []
    mock_vs.count.assert_called_once_with(COLLECTION)
    mock_vs.search.assert_not_called()


async def test_ask_with_results(monkeypatch):
    """非空库时应走 embed → search → chat 全流程并回传原始 sources。"""
    mock_vs = MagicMock()
    mock_vs.count.return_value = 2
    source = {
        "doc_id": "doc-1",
        "chunk_id": 0,
        "content": "钢网清洁：每班次生产结束后使用专用清洗剂",
        "score": 0.92,
    }
    mock_vs.search.return_value = [source]
    monkeypatch.setattr("agent_knowledge.rag_chain.vector_store", mock_vs)

    mock_llm = MagicMock()
    mock_llm.embed = AsyncMock(return_value=[[0.1, 0.2]])
    mock_llm.chat = AsyncMock(return_value="答案是每班次清洁一次")
    monkeypatch.setattr("agent_knowledge.rag_chain.llm_client", mock_llm)

    answer, sources = await ask("钢网清洁频率是多少？", top_k=5)

    assert answer == "答案是每班次清洁一次"
    assert sources == [source]
    mock_llm.embed.assert_called_once_with(["钢网清洁频率是多少？"])
    mock_vs.search.assert_called_once()
    # chat 收到 system + user 两条消息
    messages = mock_llm.chat.call_args.args[0]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    # user 模板应渲染出参考资料与问题
    assert "钢网清洁" in messages[1]["content"]
    assert "钢网清洁频率是多少？" in messages[1]["content"]


async def test_upload_document(monkeypatch):
    """上传应串联 load_and_split → embed → init_collections → insert → save_doc_meta。"""
    # 重置懒初始化标志，保证本用例触发 init_collections
    monkeypatch.setattr("agent_knowledge.rag_chain._initialized", False)
    # P0-5：_save_meta 已删除，元数据改走 doc_meta_store（AsyncMock）
    monkeypatch.setattr(
        "agent_knowledge.rag_chain.doc_meta_store.save_doc_meta", AsyncMock()
    )
    monkeypatch.setattr(
        "agent_knowledge.rag_chain.load_and_split",
        lambda content, filename: ["chunk1", "chunk2"],
    )

    mock_llm = MagicMock()
    mock_llm.embed = AsyncMock(return_value=[[0.1, 0.2], [0.3, 0.4]])
    monkeypatch.setattr("agent_knowledge.rag_chain.llm_client", mock_llm)

    mock_vs = MagicMock()
    mock_vs.insert.return_value = 2
    monkeypatch.setattr("agent_knowledge.rag_chain.vector_store", mock_vs)

    doc_id, chunk_count = await upload_document(b"manual content", "维护手册.pdf")

    assert chunk_count == 2
    assert doc_id.startswith("维护手册_")
    assert len(doc_id.split("_")[-1]) == 8
    mock_llm.embed.assert_called_once_with(["chunk1", "chunk2"])
    mock_vs.init_collections.assert_called_once_with(2)
    mock_vs.insert.assert_called_once()
