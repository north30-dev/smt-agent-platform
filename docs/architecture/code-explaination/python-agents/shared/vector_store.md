# vector_store

> Milvus 向量库封装，覆盖三个 collection：smt_knowledge、smt_fault_cases、smt_quality_cases。

**模块路径**: `shared/vector_store.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/shared/vector_store.py`

---

## 模块级常量

| 名称 | 类型 | 说明 |
|------|------|------|
| `COLLECTIONS` | `tuple` | `("smt_knowledge", "smt_fault_cases", "smt_quality_cases")` |
| `_DOC_ID_PATTERN` | `re.Pattern` | doc_id 白名单字符校验 |
| `_connected` | `bool` | Milvus 连接状态 |
| `_connect_lock` | `threading.Lock` | 连接初始化锁 |

---

## 类

### `VectorStoreError(Exception)`

> 向量库操作异常

**签名**: `class VectorStoreError(Exception)`

---

## 顶层函数

### `_validate_doc_id(doc_id: str) -> None`

> 校验 doc_id 安全性

**签名**: `def _validate_doc_id(doc_id: str) -> None`

**逻辑**: 使用白名单正则校验 doc_id，防止 filter 表达式注入

**异常**: `ValueError` — doc_id 包含非法字符

---

### `_ensure_connect() -> None`

> 懒加载 Milvus 连接

**签名**: `def _ensure_connect() -> None`

**逻辑**: 双重检查加锁模式，模块级单例连接

---

### `_build_schema(embed_dim: int) -> CollectionSchema`

> 构造 collection schema

**签名**: `def _build_schema(embed_dim: int) -> CollectionSchema`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `embed_dim` | `int` | 嵌入向量维度 |

**返回值**: `CollectionSchema` — 包含 id, doc_id, chunk_id, text, embedding 字段

---

### `init_collections(embed_dim: int) -> None`

> 初始化 collection（幂等）

**签名**: `def init_collections(embed_dim: int) -> None`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `embed_dim` | `int` | 嵌入向量维度 |

**逻辑**: 遍历 COLLECTIONS → 若不存在则创建 → 建立 IVF_FLAT + COSINE 索引

---

### `insert(collection_name: str, doc_id: str, chunks: list[str], vectors: list[list[float]]) -> int`

> 批量插入文档 chunks 与向量

**签名**: `def insert(collection_name: str, doc_id: str, chunks: list[str], vectors: list[list[float]]) -> int`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `collection_name` | `str` | 是 | Collection 名称 |
| `doc_id` | `str` | 是 | 文档 ID |
| `chunks` | `list[str]` | 是 | 文本分块列表 |
| `vectors` | `list[list[float]]` | 是 | 嵌入向量列表 |

**返回值**: `int` — 插入的记录数

---

### `search(collection_name: str, query_vector: list[float], top_k: int = 5, doc_id: str | None = None) -> list[dict]`

> 向量检索

**签名**: `def search(collection_name: str, query_vector: list[float], top_k: int = 5, doc_id: str | None = None) -> list[dict]`

**参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `collection_name` | `str` | 是 | — | Collection 名称 |
| `query_vector` | `list[float]` | 是 | — | 查询向量 |
| `top_k` | `int` | 否 | `5` | 返回结果数 |
| `doc_id` | `str \| None` | 否 | `None` | 按文档 ID 过滤 |

**返回值**: `list[dict]` — 检索结果列表（含 score, text, doc_id, chunk_id）

---

### `delete_by_doc(collection_name: str, doc_id: str) -> int`

> 删除指定 doc_id 的所有向量

**签名**: `def delete_by_doc(collection_name: str, doc_id: str) -> int`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `collection_name` | `str` | 是 | Collection 名称 |
| `doc_id` | `str` | 是 | 文档 ID |

**返回值**: `int` — 删除的记录数

---

### `list_docs(collection_name: str) -> list[dict]`

> 返回文档列表（按 doc_id 分组统计）

**签名**: `def list_docs(collection_name: str) -> list[dict]`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `collection_name` | `str` | Collection 名称 |

**返回值**: `list[dict]` — `[{doc_id, chunk_count}, ...]`

---

### `count(collection_name: str) -> int`

> 返回 collection 总条数

**签名**: `def count(collection_name: str) -> int`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `collection_name` | `str` | Collection 名称 |

**返回值**: `int` — 总记录数
