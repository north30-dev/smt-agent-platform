# agent-knowledge/document_loader

> 文档加载与切分模块，支持 .md/.txt/.pdf/.docx 四种格式。

**模块路径**: `agent-knowledge/document_loader.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-knowledge/document_loader.py`

---

## 顶层函数

### `load_and_split(content: bytes, filename: str, chunk_size: int = 500, overlap: int = 50) -> list[str]`

> 加载文档并切分为 chunks

**签名**: `def load_and_split(content: bytes, filename: str, chunk_size: int = 500, overlap: int = 50) -> list[str]`

**参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `content` | `bytes` | — | 文件内容 |
| `filename` | `str` | — | 文件名（用于判断类型） |
| `chunk_size` | `int` | `500` | 分块大小（字符数） |
| `overlap` | `int` | `50` | 重叠字符数 |

**返回值**: `list[str]` — 切分后的文本块列表

**异常**: `ValueError` — 不支持的文件类型

---

### `_load_text(content: bytes, filename: str) -> str`

> 根据文件扩展名加载文本

**签名**: `def _load_text(content: bytes, filename: str) -> str`

**支持格式**:

| 扩展名 | 加载方式 |
|--------|---------|
| `.md` / `.txt` | 直接解码为 UTF-8 |
| `.pdf` | pypdf.PdfReader 提取文本 |
| `.docx` | python-docx 提取段落文本 |

---

### `_split_text(text: str, chunk_size: int, overlap: int) -> list[str]`

> 三级切分策略

**签名**: `def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]`

**切分策略**:
1. 按双换行（段落）或 Markdown 标题（# ~ ######）切分
2. 长段落回退到句子边界切分
3. 最终回退到字符滑动窗口

---

### `_split_by_sentence(text: str, chunk_size: int, overlap: int) -> list[str]`

> 按句子边界切分

**签名**: `def _split_by_sentence(text: str, chunk_size: int, overlap: int) -> list[str]`

**逻辑**: 按 `。！？.!?\n` 分隔 → 累积到 chunk_size → 超长句子用滑动窗口（step = chunk_size - overlap）
