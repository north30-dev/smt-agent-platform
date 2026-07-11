# agent-knowledge/main

> 知识助手 Agent FastAPI 应用入口，提供文档上传、RAG 问答、文档列表、文档删除四个接口。

**模块路径**: `agent-knowledge/main.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-knowledge/main.py`

---

## 模块级常量

| 名称 | 类型 | 说明 |
|------|------|------|
| `MAX_UPLOAD_BYTES` | `int` | 最大上传大小 50MB |

---

## FastAPI 应用

```python
app = FastAPI(title="SMT 知识助手 Agent", version="0.2.0", lifespan=lifespan)
```

---

## 生命周期

### `async lifespan(app: FastAPI)`

> 应用生命周期管理

**逻辑**: 关闭时调用 `llm_client.aclose()` 释放资源

---

## REST 端点

### `POST /v1/knowledge/upload` — 上传文档

**方法**: `async def upload_file(file: UploadFile = File(...)) -> UploadResponse`

**参数**:

| 参数 | 类型 | 位置 | 说明 |
|------|------|------|------|
| `file` | `UploadFile` | Form Data | 上传的文件 |

**返回值**: `UploadResponse` — `{doc_id, doc_name, chunk_count}`

**异常处理**:
- 文件为空 → 400
- 文件超过 50MB → 413
- 不支持的文件类型 → 400

---

### `POST /v1/knowledge/ask` — RAG 问答

**方法**: `async def ask(req: AskRequest) -> AskResponse`

**参数**:

| 参数 | 类型 | 位置 | 说明 |
|------|------|------|------|
| `req` | `AskRequest` | Body | `{question: str}` |

**返回值**: `AskResponse` — `{answer, sources}`

---

### `GET /v1/knowledge/documents` — 文档列表

**方法**: `async def list_documents() -> list[DocumentInfo]`

**返回值**: `list[DocumentInfo]` — `[{doc_id, doc_name, chunk_count, create_time}]`

---

### `DELETE /v1/knowledge/documents/{doc_id}` — 删除文档

**方法**: `async def delete_document(doc_id: str) -> DeleteResponse`

**参数**:

| 参数 | 类型 | 位置 | 说明 |
|------|------|------|------|
| `doc_id` | `str` | Path | 文档 ID |

**返回值**: `DeleteResponse` — `{success, deleted_chunks}`

---

## 全局异常处理

| 异常类型 | HTTP 状态码 | 错误码 | 说明 |
|---------|------------|--------|------|
| `ValueError` | 400 | unsupported_file_type | 不支持的文件类型 |
| `LLMClientError` | 503 | llm_unavailable | 大模型服务不可用 |
| `VectorStoreError` | 503 | vector_store_unavailable | 向量库不可用 |
| `Exception` | 500 | internal_error | 内部错误 |
