"""知识助手 Agent FastAPI 应用。

端口 8004。提供文档上传、RAG 问答、文档列表、文档删除四个接口。
对外路径前缀 /knowledge/**（经 smt-gateway StripPrefix=2 后落地本服务）。
"""

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from shared.llm_client import LLMClientError
from shared.models import ErrorResponse
from shared.vector_store import VectorStoreError

from . import rag_chain
from .models import (
    AskRequest,
    AskResponse,
    DeleteResponse,
    DocumentInfo,
    SourceItem,
    UploadResponse,
)

app = FastAPI(
    title="SMT 知识助手 Agent",
    description="知识库 RAG 问答服务，支持文档上传、检索问答、文档管理。",
    version="0.2.0",
)


@app.post("/knowledge/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    """上传知识文档，解析切分向量化后写入 Milvus。"""
    content = await file.read()
    if not content:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error="unsupported_file_type", message="上传文件不能为空"
            ).model_dump(),
        )
    filename = file.filename or "unknown"
    doc_id, chunk_count = await rag_chain.upload_document(content, filename)
    return UploadResponse(doc_id=doc_id, doc_name=filename, chunk_count=chunk_count)


@app.post("/knowledge/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    """基于知识库的 RAG 检索增强问答。"""
    answer, sources = await rag_chain.ask(req.question)
    source_items = [
        SourceItem(
            doc_id=s["doc_id"],
            chunk_id=s["chunk_id"],
            score=s["score"],
            snippet=s.get("snippet", s.get("content", "")),
        )
        for s in sources
    ]
    return AskResponse(answer=answer, sources=source_items)


@app.get("/knowledge/documents", response_model=list[DocumentInfo])
async def list_documents():
    """查询知识库全部文档元信息。"""
    return [DocumentInfo(**doc) for doc in await rag_chain.list_documents()]


@app.delete("/knowledge/documents/{doc_id}", response_model=DeleteResponse)
async def delete_document(doc_id: str):
    """根据 doc_id 删除文档及其全部分块向量。"""
    deleted = await rag_chain.delete_document(doc_id)
    return DeleteResponse(success=True, deleted_chunks=deleted)


@app.exception_handler(ValueError)
async def value_error_handler(_request, exc: ValueError):
    """不支持的文件类型等参数错误 → 400。"""
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error="unsupported_file_type", message=str(exc)
        ).model_dump(),
    )


@app.exception_handler(LLMClientError)
async def llm_error_handler(_request, exc: LLMClientError):
    """大模型不可达 → 503。"""
    return JSONResponse(
        status_code=503,
        content=ErrorResponse(
            error="llm_unavailable", message=str(exc)
        ).model_dump(),
    )


@app.exception_handler(VectorStoreError)
async def vector_store_error_handler(_request, exc: VectorStoreError):
    """向量库不可达 → 503。"""
    return JSONResponse(
        status_code=503,
        content=ErrorResponse(
            error="vector_store_unavailable", message=str(exc)
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def internal_error_handler(_request, exc: Exception):
    """未知异常兜底 → 500。"""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="internal_error", message="内部错误"
        ).model_dump(),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("agent-knowledge.main:app", host="0.0.0.0", port=8004, reload=True)
