"""大模型统一调用出口。

封装 OpenAI 兼容的 chat 与 embedding 接口。
按 AGENTS.md §3.2 要求，禁止在各 Agent 内直接 new client，统一走本模块。

P0 B1：全接口改 async，使用 httpx.AsyncClient 避免阻塞 uvicorn worker 事件循环。
M1+m1：引入 tenacity 重试（仅对网络错误和 429/5xx 重试）+ 模块级共享 AsyncClient 连接池复用。
"""

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from shared.config import settings


class LLMClientError(Exception):
    """大模型调用异常。"""


class _RetryableHTTPError(Exception):
    """可重试的 HTTP 状态码（429/5xx），内部使用。"""


# m1：模块级共享 AsyncClient，连接池复用
_client_instance: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    """获取共享 AsyncClient 实例（懒初始化，连接池复用）。

    测试时可通过 _reset_client() 重置后注入 mock。
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = httpx.AsyncClient(
            timeout=60,
            limits=httpx.Limits(max_connections=settings.http_max_connections),
        )
    return _client_instance


def _reset_client() -> None:
    """重置共享客户端（仅供测试使用）。"""
    global _client_instance
    _client_instance = None


async def aclose() -> None:
    """关闭共享 AsyncClient（供 FastAPI lifespan shutdown 调用）。

    幂等：客户端未创建或已关闭时直接返回。
    """
    global _client_instance
    if _client_instance is not None:
        await _client_instance.aclose()
        _client_instance = None


def _headers() -> dict:
    """构造鉴权请求头。"""
    return {"Authorization": f"Bearer {settings.llm_api_key}"}


async def chat(messages: list[dict], temperature: float = 0.3) -> str:
    """调用大模型对话接口。

    Args:
        messages: 消息列表，格式同 OpenAI：
            [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        temperature: 采样温度，默认 0.3。

    Returns:
        assistant 回复文本。

    Raises:
        LLMClientError: 网络错误、HTTP 非 2xx 或响应解析失败。
    """
    url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": settings.llm_max_tokens,
        "frequency_penalty": settings.llm_frequency_penalty,
    }

    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(settings.llm_max_retries + 1),
            wait=wait_exponential(
                multiplier=settings.llm_retry_backoff, min=1, max=10
            ),
            retry=retry_if_exception_type(
                (httpx.TimeoutException, httpx.ConnectError, _RetryableHTTPError)
            ),
            reraise=True,
        ):
            with attempt:
                client = _get_client()
                try:
                    resp = await client.post(url, json=payload, headers=_headers())
                except (httpx.TimeoutException, httpx.ConnectError):
                    raise
                except httpx.HTTPError as exc:
                    raise LLMClientError(f"调用大模型对话接口失败：{exc}") from exc

                if resp.status_code in (429, 500, 502, 503, 504):
                    raise _RetryableHTTPError(
                        f"大模型对话接口返回可重试状态码：status={resp.status_code}"
                    )
                if resp.status_code // 100 != 2:
                    raise LLMClientError(
                        f"大模型对话接口返回非 2xx：status={resp.status_code}, body={resp.text}"
                    )
                try:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    if not content or not content.strip():
                        raise LLMClientError(
                            "大模型返回空内容（content 为空），模型可能陷入推理循环"
                        )
                    return content
                except (ValueError, KeyError, IndexError) as exc:
                    raise LLMClientError(f"解析大模型对话响应失败：{exc}") from exc
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        raise LLMClientError(f"大模型对话接口重试耗尽：{exc}") from exc


async def embed(texts: list[str]) -> list[list[float]]:
    """调用 embedding 接口。

    Args:
        texts: 待向量化文本列表。

    Returns:
        每个文本对应的向量，顺序与入参一致。

    Raises:
        LLMClientError: 网络错误、HTTP 非 2xx 或响应解析失败。
    """
    url = f"{settings.llm_base_url.rstrip('/')}/embeddings"
    payload = {"model": settings.llm_embed_model, "input": texts}

    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(settings.llm_max_retries + 1),
            wait=wait_exponential(
                multiplier=settings.llm_retry_backoff, min=1, max=10
            ),
            retry=retry_if_exception_type(
                (httpx.TimeoutException, httpx.ConnectError, _RetryableHTTPError)
            ),
            reraise=True,
        ):
            with attempt:
                client = _get_client()
                try:
                    resp = await client.post(url, json=payload, headers=_headers())
                except (httpx.TimeoutException, httpx.ConnectError):
                    raise
                except httpx.HTTPError as exc:
                    raise LLMClientError(f"调用 embedding 接口失败：{exc}") from exc

                if resp.status_code in (429, 500, 502, 503, 504):
                    raise _RetryableHTTPError(
                        f"embedding 接口返回可重试状态码：status={resp.status_code}"
                    )
                if resp.status_code // 100 != 2:
                    raise LLMClientError(
                        f"embedding 接口返回非 2xx：status={resp.status_code}, body={resp.text}"
                    )
                try:
                    data = resp.json()
                    sorted_data = sorted(data["data"], key=lambda item: item["index"])
                    return [item["embedding"] for item in sorted_data]
                except (ValueError, KeyError, IndexError, TypeError) as exc:
                    raise LLMClientError(f"解析 embedding 响应失败：{exc}") from exc
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        raise LLMClientError(f"embedding 接口重试耗尽：{exc}") from exc
