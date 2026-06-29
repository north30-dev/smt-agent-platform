"""RAG 流程封装。

串联文档加载切分、向量化、Milvus 存取与大模型对话，
对上暴露上传、问答、列举、删除四个原子能力。
错误不在本模块捕获，统一交由 main.py 异常处理器兜底。

P0 B1：全接口改 async，pymilvus 同步调用用 asyncio.to_thread 包装。
P0-5：文档元数据从 doc_meta.json 迁移到 PostgreSQL（shared/doc_meta_store）。
"""

import asyncio
import threading
import uuid
from functools import lru_cache
from pathlib import Path

import yaml

from shared import doc_meta_store, llm_client, vector_store

from .document_loader import load_and_split

# 知识库 collection 名
COLLECTION = "smt_knowledge"

# Prompt 模板文件
_PROMPT_FILE = Path(__file__).parent.parent / "shared" / "prompts" / "system_prompt.yaml"

# 模块级懒初始化标志与保护锁（P0 B2：防止多线程并发 check-then-set 竞态）
_initialized = False
_init_lock = threading.Lock()


async def upload_document(content: bytes, filename: str) -> tuple[str, int]:
    """加载切分 → embed → insert 到 Milvus。

    Args:
        content: 文件原始字节。
        filename: 文件名。

    Returns:
        (doc_id, chunk_count)。
    """
    global _initialized

    doc_id = f"{Path(filename).stem}_{uuid.uuid4().hex[:8]}"
    chunks = await asyncio.to_thread(load_and_split, content, filename)
    if not chunks:
        await doc_meta_store.save_doc_meta(doc_id, filename)
        return doc_id, 0

    vectors = await llm_client.embed(chunks)

    if not _initialized:
        with _init_lock:
            if not _initialized:
                await asyncio.to_thread(vector_store.init_collections, len(vectors[0]))
                _initialized = True

    chunk_count = await asyncio.to_thread(
        vector_store.insert, COLLECTION, doc_id, chunks, vectors
    )
    await doc_meta_store.save_doc_meta(doc_id, filename)
    return doc_id, chunk_count


async def ask(question: str, top_k: int = 5) -> tuple[str, list[dict]]:
    """RAG 问答：embed 问题 → search → 拼 context → llm chat。

    Args:
        question: 用户问题。
        top_k: 检索条数，默认 5。

    Returns:
        (answer, sources)，sources 为检索结果原始列表。
        空知识库直接返回 ("知识库为空，请先上传文档。", [])。
    """
    if await asyncio.to_thread(vector_store.count, COLLECTION) == 0:
        return "知识库为空，请先上传文档。", []

    query_vector = (await llm_client.embed([question]))[0]
    sources = await asyncio.to_thread(
        vector_store.search, COLLECTION, query_vector, top_k
    )

    context = "\n\n".join(
        f"[{i + 1}] {s['content']}" for i, s in enumerate(sources)
    )
    system_prompt, user_template = _load_prompts()
    user_content = user_template.format(context=context, question=question)

    answer = await llm_client.chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
    )
    return answer, sources


async def list_documents() -> list[dict]:
    """返回 [{doc_id, doc_name, chunk_count, create_time}]。"""
    meta = await doc_meta_store.list_doc_meta()
    docs = await asyncio.to_thread(vector_store.list_docs, COLLECTION)
    result: list[dict] = []
    for item in docs:
        doc_id = item["doc_id"]
        info = meta.get(doc_id, {})
        result.append(
            {
                "doc_id": doc_id,
                "doc_name": info.get("doc_name", doc_id),
                "chunk_count": item["chunk_count"],
                "create_time": info.get("create_time", ""),
            }
        )
    return result


async def delete_document(doc_id: str) -> int:
    """删除指定 doc_id 的所有向量。

    Args:
        doc_id: 文档唯一标识。

    Returns:
        实际删除的条数。
    """
    deleted = await asyncio.to_thread(vector_store.delete_by_doc, COLLECTION, doc_id)
    await doc_meta_store.remove_doc_meta(doc_id)
    return deleted


@lru_cache(maxsize=1)
def _load_prompts() -> tuple[str, str]:
    """读取 system_prompt.yaml 中的 knowledge.system 与 user_template。

    Prompt 文件运行期不变，用 lru_cache 避免每次请求重复读盘（P0 M5）。
    """
    with _PROMPT_FILE.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    knowledge = data["knowledge"]
    return knowledge["system"], knowledge["user_template"]
