"""shared.vector_store 单元测试。

使用 monkeypatch 替换 shared.vector_store 模块内的 pymilvus 符号
（connections / Collection / utility），不依赖真实 Milvus 服务。
"""

from unittest.mock import MagicMock

import pytest

from shared import vector_store


@pytest.fixture
def mock_milvus(monkeypatch):
    """统一 mock shared.vector_store 内的 pymilvus 模块级符号。"""
    fake_col = MagicMock()
    fake_col.num_entities = 0
    fake_collection_cls = MagicMock(return_value=fake_col)
    fake_connections = MagicMock()
    fake_utility = MagicMock()
    fake_utility.has_collection.return_value = False

    monkeypatch.setattr(vector_store, "Collection", fake_collection_cls)
    monkeypatch.setattr(vector_store, "connections", fake_connections)
    monkeypatch.setattr(vector_store, "utility", fake_utility)
    # 重置连接单例标志，确保每次测试都重新走连接流程
    monkeypatch.setattr(vector_store, "_connected", False)

    return {
        "col": fake_col,
        "collection_cls": fake_collection_cls,
        "connections": fake_connections,
        "utility": fake_utility,
    }


def test_init_collections(mock_milvus):
    """三个 collection 均不存在时应创建并建立索引。"""
    vector_store.init_collections(768)

    # 三个 collection 都调用过 Collection 构造
    assert mock_milvus["collection_cls"].call_count == 3
    # create_index 至少调用一次
    mock_milvus["col"].create_index.assert_called()


def test_insert(mock_milvus):
    """批量插入应返回插入条数，并触发 insert 与 flush。"""
    chunks = ["chunk0", "chunk1", "chunk2"]
    vectors = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]

    n = vector_store.insert("smt_knowledge", "doc-1", chunks, vectors)

    assert n == 3
    mock_milvus["col"].insert.assert_called_once()
    mock_milvus["col"].flush.assert_called()


def test_search_empty(mock_milvus):
    """空命中时返回空列表。"""
    mock_milvus["col"].search.return_value = [[]]

    result = vector_store.search("smt_knowledge", [0.1, 0.2], top_k=5)

    assert result == []


def test_search_with_results(mock_milvus):
    """带 score 的命中应解析为 [{doc_id, chunk_id, content, score}]。"""
    hit = MagicMock()
    hit.score = 0.95
    hit.entity.get.side_effect = lambda key: {
        "doc_id": "doc-1",
        "chunk_id": 0,
        "content": "故障案例内容",
    }[key]
    mock_milvus["col"].search.return_value = [[hit]]

    result = vector_store.search("smt_knowledge", [0.1, 0.2], top_k=5)

    assert result == [
        {
            "doc_id": "doc-1",
            "chunk_id": 0,
            "content": "故障案例内容",
            "score": pytest.approx(0.95),
        }
    ]
