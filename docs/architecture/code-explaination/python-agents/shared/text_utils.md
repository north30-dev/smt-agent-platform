# text_utils

> 文本处理工具函数，提供文本截断与 JSON 提取能力。

**模块路径**: `shared/text_utils.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/shared/text_utils.py`

---

## 模块级常量

| 名称 | 类型 | 说明 |
|------|------|------|
| `_TRUNCATE_SUFFIX` | `str` | `"...(截断)"` 截断后缀 |

---

## 顶层函数

### `truncate(text: str, max_chars: int) -> str`

> 截断文本以避免 prompt 过长

**签名**: `def truncate(text: str, max_chars: int) -> str`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `text` | `str` | 是 | 待截断文本 |
| `max_chars` | `int` | 是 | 最大字符数 |

**返回值**: `str` — 截断后的文本（保证长度 ≤ max_chars）

---

### `extract_json_block(text: str) -> str | None`

> 从 markdown 代码块或裸 JSON 中提取 JSON 文本

**签名**: `def extract_json_block(text: str) -> str | None`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `text` | `str` | 待提取文本 |

**返回值**: `str | None` — 提取的 JSON 文本，未找到返回 None

**逻辑**: 先尝试匹配 ` ```json ... ``` ` 代码块 → 再尝试匹配 ` ``` ... ``` ` 代码块 → 最后尝试裸 JSON
