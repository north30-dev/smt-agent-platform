"""Milvus 向量库封装。

覆盖两个 collection：smt_knowledge（知识库）、smt_fault_cases（故障案例）。
提供 collection 初始化、批量插入、向量检索、按文档删除、文档列表、条数统计等同步能力。
"""

import threading

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    MilvusException,
    connections,
    utility,
)
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from shared.config import settings


class VectorStoreError(Exception):
    """向量库操作异常。"""


# 受管理的 collection 名称
COLLECTIONS = ("smt_knowledge", "smt_fault_cases")

# 模块级连接单例标志与保护锁（P0 B2：防止多线程并发 check-then-set 竞态）
_connected = False
_connect_lock = threading.Lock()


def _ensure_connect() -> None:
    """懒加载 Milvus 连接（模块级单例，双重检查加锁）。"""
    global _connected
    if _connected:
        return
    with _connect_lock:
        if _connected:
            return
        try:
            for attempt in Retrying(
                stop=stop_after_attempt(settings.milvus_max_retries + 1),
                wait=wait_exponential(
                    multiplier=settings.milvus_retry_backoff, min=1, max=10
                ),
                retry=retry_if_exception_type((MilvusException, OSError)),
                reraise=True,
            ):
                with attempt:
                    connections.connect(
                        alias="default",
                        host=settings.milvus_host,
                        port=str(settings.milvus_port),
                    )
        except Exception as exc:
            raise VectorStoreError(f"连接 Milvus 失败：{exc}") from exc
        _connected = True


def _build_schema(embed_dim: int) -> CollectionSchema:
    """构造 collection schema。"""
    fields = [
        FieldSchema(
            name="id",
            dtype=DataType.VARCHAR,
            is_primary=True,
            auto_id=False,
            max_length=64,
        ),
        FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name="chunk_id", dtype=DataType.INT64),
        FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=embed_dim),
    ]
    return CollectionSchema(fields=fields, auto_id=False, description="SMT 向量集合")


def _get_collection(collection_name: str) -> Collection:
    """加载并返回 collection 句柄。"""
    _ensure_connect()
    try:
        col = Collection(name=collection_name)
        col.load()
        return col
    except Exception as exc:
        raise VectorStoreError(f"加载 collection {collection_name} 失败：{exc}") from exc


def init_collections(embed_dim: int) -> None:
    """若 collection 不存在则创建，并建立 IVF_FLAT + COSINE 索引。

    Args:
        embed_dim: 向量维度。
    """
    _ensure_connect()
    for name in COLLECTIONS:
        try:
            if utility.has_collection(name):
                continue
            schema = _build_schema(embed_dim)
            col = Collection(name=name, schema=schema)
            col.create_index(
                field_name="vector",
                index_params={
                    "index_type": "IVF_FLAT",
                    "metric_type": "COSINE",
                    "params": {"nlist": 128},
                },
            )
        except Exception as exc:
            raise VectorStoreError(f"创建 collection {name} 失败：{exc}") from exc


def insert(
    collection_name: str,
    doc_id: str,
    chunks: list[str],
    vectors: list[list[float]],
) -> int:
    """批量插入文档 chunks 与向量。

    Args:
        collection_name: collection 名称。
        doc_id: 文档唯一标识。
        chunks: 文本分块列表。
        vectors: 与 chunks 一一对应的向量列表。

    Returns:
        插入条数。

    Raises:
        VectorStoreError: 长度不一致或插入失败。
    """
    if len(chunks) != len(vectors):
        raise VectorStoreError("chunks 与 vectors 长度不一致")
    if not chunks:
        return 0
    col = _get_collection(collection_name)
    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    doc_ids = [doc_id] * len(chunks)
    chunk_ids = list(range(len(chunks)))
    try:
        for attempt in Retrying(
            stop=stop_after_attempt(settings.milvus_max_retries + 1),
            wait=wait_exponential(
                multiplier=settings.milvus_retry_backoff, min=1, max=10
            ),
            retry=retry_if_exception_type((MilvusException, OSError)),
            reraise=True,
        ):
            with attempt:
                col.insert([ids, doc_ids, chunk_ids, chunks, vectors])
                col.flush()
    except Exception as exc:
        raise VectorStoreError(
            f"插入 collection {collection_name} 失败：{exc}"
        ) from exc
    return len(chunks)


def search(
    collection_name: str,
    query_vector: list[float],
    top_k: int = 5,
    doc_id: str | None = None,
) -> list[dict]:
    """向量检索。

    Args:
        collection_name: collection 名称。
        query_vector: 查询向量。
        top_k: 返回条数，默认 5。
        doc_id: 可选，按 doc_id 过滤。

    Returns:
        [{doc_id, chunk_id, content, score}]，score 越高越相似。空库返回空列表。
    """
    col = _get_collection(collection_name)
    expr = f'doc_id == "{doc_id}"' if doc_id else None
    search_params = {"metric_type": "COSINE", "params": {"nprobe": 16}}
    try:
        results = col.search(
            data=[query_vector],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["doc_id", "chunk_id", "content"],
        )
    except Exception as exc:
        raise VectorStoreError(
            f"检索 collection {collection_name} 失败：{exc}"
        ) from exc

    output: list[dict] = []
    hits = results[0] if results else []
    for hit in hits:
        entity = hit.entity
        output.append(
            {
                "doc_id": entity.get("doc_id"),
                "chunk_id": entity.get("chunk_id"),
                "content": entity.get("content"),
                "score": float(hit.score),
            }
        )
    return output


def delete_by_doc(collection_name: str, doc_id: str) -> int:
    """删除指定 doc_id 的所有向量。

    Args:
        collection_name: collection 名称。
        doc_id: 文档唯一标识。

    Returns:
        删除条数。
    """
    col = _get_collection(collection_name)
    expr = f'doc_id == "{doc_id}"'
    try:
        # 用 query_iterator 突破 pymilvus 默认 16384 上限（P0 M4）
        iterator = col.query_iterator(expr=expr, output_fields=["id"], batch_size=1000)
        to_delete = 0
        batch = next(iterator, None)
        while batch:
            to_delete += len(batch)
            batch = next(iterator, None)
    except Exception as exc:
        raise VectorStoreError(
            f"查询 collection {collection_name} 中 doc_id={doc_id} 失败：{exc}"
        ) from exc
    if to_delete > 0:
        try:
            col.delete(expr=expr)
            col.flush()
        except Exception as exc:
            raise VectorStoreError(
                f"删除 collection {collection_name} 中 doc_id={doc_id} 失败：{exc}"
            ) from exc
    return to_delete


def list_docs(collection_name: str) -> list[dict]:
    """返回 [{doc_id, chunk_count}]，按 doc_id 分组统计。"""
    col = _get_collection(collection_name)
    try:
        # 用 query_iterator 突破 pymilvus 默认 16384 上限（P0 M4）
        iterator = col.query_iterator(
            expr="chunk_id >= 0", output_fields=["doc_id"], batch_size=1000
        )
        counts: dict[str, int] = {}
        batch = next(iterator, None)
        while batch:
            for row in batch:
                d = row.get("doc_id")
                counts[d] = counts.get(d, 0) + 1
            batch = next(iterator, None)
    except Exception as exc:
        raise VectorStoreError(
            f"列举 collection {collection_name} 文档失败：{exc}"
        ) from exc
    return [{"doc_id": d, "chunk_count": c} for d, c in counts.items()]


def count(collection_name: str) -> int:
    """返回 collection 总条数，用于空库兜底判断。"""
    col = _get_collection(collection_name)
    try:
        col.flush()
        return int(col.num_entities)
    except Exception as exc:
        raise VectorStoreError(
            f"统计 collection {collection_name} 条数失败：{exc}"
        ) from exc
