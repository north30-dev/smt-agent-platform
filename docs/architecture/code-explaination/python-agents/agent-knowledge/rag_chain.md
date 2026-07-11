# agent-knowledge/rag_chain

> RAG 流程封装，串联文档加载切分、向量化、Milvus 存取与大模型对话。

**模块路径**: `agent-knowledge/rag_chain.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-knowledge/rag_chain.py`

---

## 模块级常量

| 名称 | 类型 | 说明 |
|------|------|------|
| `COLLECTION` | `str` | `"smt_knowledge"` |
| `_PROMPT_FILE` | `Path` | 提示词模板路径 |
| `_initialized` | `bool` | collection 是否已初始化 |
| `_init_lock` | `threading.Lock` | 初始化锁 |

---

## 顶层函数

### `async upload_document(content: bytes, filename: str) -> tuple[str, int]`

> 上传文档并建立向量索引

**签名**: `async def upload_document(content: bytes, filename: str) -> tuple[str, int]`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `content` | `bytes` | 是 | 文件内容 |
| `filename` | `str` | 是 | 文件名 |

**返回值**: `tuple[str, int]` — (doc_id, chunk_count)

**逻辑**:
1. 生成 `doc_id = filename_stem + uuid8`
2. 调用 `load_and_split` 切分文档（asyncio.to_thread 包装同步调用）
3. 嵌入向量（llm_client.embed）
4. 双重检查锁初始化 Milvus collection
5. 插入向量到 Milvus
6. 保存文档元数据到 PostgreSQL

---

### `async ask(question: str, top_k: int = 5) -> tuple[str, list[dict]]`

> RAG 问答

**签名**: `async def ask(question: str, top_k: int = 5) -> tuple[str, list[dict]]`

**参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `question` | `str` | — | 用户问题 |
| `top_k` | `int` | `5` | 检索结果数 |

**返回值**: `tuple[str, list[dict]]` — (answer, sources)

**逻辑**:
1. 检查 collection 是否为空（空则返回提示）
2. 嵌入问题 → Milvus 向量检索
3. 构建编号上下文
4. 加载提示词模板（@lru_cache 缓存）
5. 用户输入包裹在 `<user_input>` 标签中（SEC-3 数据隔离）
6. 调用 llm_client.chat
7. 返回 (answer, sources)

---

### `async list_documents() -> list[dict]`

> 列出所有文档

**签名**: `async def list_documents() -> list[dict]`

**返回值**: `list[dict]` — `[{doc_id, doc_name, chunk_count, create_time}]`

**逻辑**: 合并 PostgreSQL 元数据 + Milvus 分块统计

---

### `async delete_document(doc_id: str) -> int`

> 删除文档

**签名**: `async def delete_document(doc_id: str) -> int`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `doc_id` | `str` | 文档 ID |

**返回值**: `int` — 删除的分块数量

**逻辑**: 删除 Milvus 向量 → 删除 PostgreSQL 元数据

---

### `_load_prompts() -> tuple[str, str]`

> 加载提示词模板

**签名**: `def _load_prompts() -> tuple[str, str]`

**注解**: `@lru_cache(maxsize=1)`

**返回值**: `tuple[str, str]` — (system_prompt, user_template)
