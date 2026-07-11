# agent-knowledge/models

> 知识助手 Agent 的 Pydantic 请求/响应模型。

**模块路径**: `agent-knowledge/models.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-knowledge/models.py`

---

## 类

### `AskRequest(BaseModel)`

> 问答请求

**字段**:

| 字段 | 类型 | 校验 | 说明 |
|------|------|------|------|
| `question` | `str` | `min_length=1, max_length=500` | 用户问题 |

---

### `SourceItem(BaseModel)`

> 来源片段

**字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `doc_id` | `str` | 来源文档 ID |
| `chunk_id` | `int` | 来源分块 ID |
| `score` | `float` | 相似度得分 |
| `snippet` | `str` | 命中文本片段 |

---

### `AskResponse(BaseModel)`

> 问答响应

**字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `answer` | `str` | 大模型生成的答案 |
| `sources` | `list[SourceItem]` | 命中的来源片段列表 |

---

### `DocumentInfo(BaseModel)`

> 文档信息

**字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `doc_id` | `str` | 文档 ID |
| `doc_name` | `str` | 文档名称 |
| `chunk_count` | `int` | 分块数量 |
| `create_time` | `str` | 入库时间（ISO-8601） |

---

### `UploadResponse(BaseModel)`

> 上传响应

**字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `doc_id` | `str` | 文档 ID |
| `doc_name` | `str` | 文档名称 |
| `chunk_count` | `int` | 分块数量 |

---

### `DeleteResponse(BaseModel)`

> 删除响应

**字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | `bool` | 是否删除成功 |
| `deleted_chunks` | `int` | 实际删除的分块数量 |
