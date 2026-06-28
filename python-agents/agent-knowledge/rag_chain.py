"""RAG 流程封装。

串联文档加载切分、向量化、Milvus 存取与大模型对话，
对上暴露上传、问答、列举、删除四个原子能力。
错误不在本模块捕获，统一交由 main.py 异常处理器兜底。
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

from shared import llm_client, vector_store

from .document_loader import load_and_split

# 知识库 collection 名
COLLECTION = "smt_knowledge"

# 元数据持久化文件（记录 doc_id -> {doc_name, create_time}）
_META_FILE = Path(__file__).parent / "data" / "doc_meta.json"

# Prompt 模板文件
_PROMPT_FILE = Path(__file__).parent.parent / "shared" / "prompts" / "system_prompt.yaml"

# 模块级懒初始化标志，避免每次上传都重复建表建索引
_initialized = False


def upload_document(content: bytes, filename: str) -> tuple[str, int]:
    """加载切分 → embed → insert 到 Milvus。

    Args:
        content: 文件原始字节。
        filename: 文件名。

    Returns:
        (doc_id, chunk_count)。
    """
    global _initialized

    doc_id = f"{Path(filename).stem}_{uuid.uuid4().hex[:8]}"
    chunks = load_and_split(content, filename)
    if not chunks:
        _save_meta(doc_id, filename)
        return doc_id, 0

    vectors = llm_client.embed(chunks)

    if not _initialized:
        vector_store.init_collections(len(vectors[0]))
        _initialized = True

    chunk_count = vector_store.insert(COLLECTION, doc_id, chunks, vectors)
    _save_meta(doc_id, filename)
    return doc_id, chunk_count


def ask(question: str, top_k: int = 5) -> tuple[str, list[dict]]:
    """RAG 问答：embed 问题 → search → 拼 context → llm chat。

    Args:
        question: 用户问题。
        top_k: 检索条数，默认 5。

    Returns:
        (answer, sources)，sources 为检索结果原始列表。
        空知识库直接返回 ("知识库为空，请先上传文档。", [])。
    """
    if vector_store.count(COLLECTION) == 0:
        return "知识库为空，请先上传文档。", []

    query_vector = llm_client.embed([question])[0]
    sources = vector_store.search(COLLECTION, query_vector, top_k=top_k)

    context = "\n\n".join(
        f"[{i + 1}] {s['content']}" for i, s in enumerate(sources)
    )
    system_prompt, user_template = _load_prompts()
    user_content = user_template.format(context=context, question=question)

    answer = llm_client.chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
    )
    return answer, sources


def list_documents() -> list[dict]:
    """返回 [{doc_id, doc_name, chunk_count, create_time}]。"""
    meta = _load_meta()
    docs = vector_store.list_docs(COLLECTION)
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


def delete_document(doc_id: str) -> int:
    """删除指定 doc_id 的所有向量。

    Args:
        doc_id: 文档唯一标识。

    Returns:
        实际删除的条数。
    """
    deleted = vector_store.delete_by_doc(COLLECTION, doc_id)
    _remove_meta(doc_id)
    return deleted


def _load_prompts() -> tuple[str, str]:
    """读取 system_prompt.yaml 中的 knowledge.system 与 user_template。"""
    with _PROMPT_FILE.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    knowledge = data["knowledge"]
    return knowledge["system"], knowledge["user_template"]


def _load_meta() -> dict:
    """读取文档元数据。文件不存在或损坏时返回空 dict。"""
    if not _META_FILE.exists():
        return {}
    try:
        with _META_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (ValueError, OSError):
        return {}


def _save_meta(doc_id: str, filename: str) -> None:
    """追加或更新一条文档元数据。"""
    _META_FILE.parent.mkdir(parents=True, exist_ok=True)
    meta = _load_meta()
    meta[doc_id] = {
        "doc_name": filename,
        "create_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with _META_FILE.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def _remove_meta(doc_id: str) -> None:
    """删除一条文档元数据。"""
    if not _META_FILE.exists():
        return
    meta = _load_meta()
    if doc_id in meta:
        meta.pop(doc_id)
        with _META_FILE.open("w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
