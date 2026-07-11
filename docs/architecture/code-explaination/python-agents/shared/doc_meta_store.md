# doc_meta_store

> 文档元数据 PostgreSQL 存储，管理知识库文档的元数据信息。

**模块路径**: `shared/doc_meta_store.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/shared/doc_meta_store.py`

---

## 顶层函数

### `async save_doc_meta(doc_id: str, doc_name: str) -> None`

> 插入或更新文档元数据（UPSERT）

**签名**: `async def save_doc_meta(doc_id: str, doc_name: str) -> None`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `doc_id` | `str` | 是 | 文档 ID |
| `doc_name` | `str` | 是 | 文档名称 |

---

### `async list_doc_meta() -> dict[str, dict]`

> 返回所有文档元数据

**签名**: `async def list_doc_meta() -> dict[str, dict]`

**返回值**: `dict[str, dict]` — `{doc_id: {doc_name, create_time}}`

---

### `async remove_doc_meta(doc_id: str) -> None`

> 删除指定 doc_id 的元数据

**签名**: `async def remove_doc_meta(doc_id: str) -> None`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `doc_id` | `str` | 文档 ID |
