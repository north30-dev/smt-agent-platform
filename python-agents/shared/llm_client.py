"""大模型统一调用出口。

封装 OpenAI 兼容的 chat 与 embedding 接口。
按 AGENTS.md §3.2 要求，禁止在各 Agent 内直接 new client，统一走本模块。

P0 B1：全接口改 async，使用 httpx.AsyncClient 避免阻塞 uvicorn worker 事件循环。
"""

import httpx

from shared.config import settings


class LLMClientError(Exception):
    """大模型调用异常。"""


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
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload, headers=_headers())
    except httpx.HTTPError as exc:
        raise LLMClientError(f"调用大模型对话接口失败：{exc}") from exc

    if resp.status_code // 100 != 2:
        raise LLMClientError(
            f"大模型对话接口返回非 2xx：status={resp.status_code}, body={resp.text}"
        )
    try:
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError) as exc:
        raise LLMClientError(f"解析大模型对话响应失败：{exc}") from exc


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
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload, headers=_headers())
    except httpx.HTTPError as exc:
        raise LLMClientError(f"调用 embedding 接口失败：{exc}") from exc

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
