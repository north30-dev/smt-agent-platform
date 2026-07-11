# llm_client

> 大模型统一调用出口，封装 OpenAI 兼容的 chat 与 embedding 接口。

**模块路径**: `shared/llm_client.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/shared/llm_client.py`

---

## 模块级对象

| 名称 | 类型 | 说明 |
|------|------|------|
| `_client_instance` | `httpx.AsyncClient \| None` | 共享 HTTP 客户端单例 |

---

## 类

### `LLMClientError(Exception)`

> 大模型调用异常

**签名**: `class LLMClientError(Exception)`

---

### `_RetryableHTTPError(Exception)`

> 可重试的 HTTP 状态码（429/5xx），内部使用

**签名**: `class _RetryableHTTPError(Exception)`

---

## 顶层函数

### `_get_client() -> httpx.AsyncClient`

> 获取共享 AsyncClient 实例

**签名**: `def _get_client() -> httpx.AsyncClient`

**返回值**: `httpx.AsyncClient` — 懒初始化的 HTTP 客户端（连接池复用）

**逻辑**: 检查 `_client_instance` 是否为 None → 是则创建 `httpx.AsyncClient(timeout=60.0)`

---

### `_reset_client() -> None`

> 重置共享客户端（仅供测试）

**签名**: `def _reset_client() -> None`

**逻辑**: 将 `_client_instance` 设为 None

---

### `async aclose() -> None`

> 关闭共享 AsyncClient

**签名**: `async def aclose() -> None`

**逻辑**: 调用 `_client_instance.aclose()`（幂等）

---

### `_headers() -> dict`

> 构造鉴权请求头

**签名**: `def _headers() -> dict`

**返回值**: `dict` — 包含 `Authorization: Bearer <api_key>` 和 `Content-Type: application/json`

---

### `async chat(messages: list[dict], temperature: float = 0.3) -> str`

> 调用大模型对话接口

**签名**: `async def chat(messages: list[dict], temperature: float = 0.3) -> str`

**参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `messages` | `list[dict]` | 是 | — | 消息列表（role/content 格式） |
| `temperature` | `float` | 否 | `0.3` | 温度参数 |

**返回值**: `str` — 模型生成的文本

**异常**: `LLMClientError` — 调用失败时

**逻辑**: 构建请求体 → POST `/chat/completions` → tenacity 重试（3次，指数退避） → 解析响应

---

### `async embed(texts: list[str]) -> list[list[float]]`

> 调用 embedding 接口

**签名**: `async def embed(texts: list[str]) -> list[list[float]]`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `texts` | `list[str]` | 是 | 待嵌入文本列表 |

**返回值**: `list[list[float]]` — 嵌入向量列表

**异常**: `LLMClientError` — 调用失败时

**逻辑**: 构建请求体 → POST `/embeddings` → tenacity 重试 → 按 index 排序返回向量
