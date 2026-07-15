"""大模型统一调用出口（OpenAI SDK 版本）。

封装 OpenAI 兼容的 chat 与 embedding 接口。
按 AGENTS.md §3.2 要求，禁止在各 Agent 内直接 new client，统一走本模块。

改用 openai.AsyncOpenAI 替代 httpx 手动请求，代码量从 ~180 行缩减到 ~120 行。
"""

import asyncio

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)

from shared.config import settings


class LLMClientError(Exception):
    """大模型调用异常。"""


# 模块级共享 AsyncOpenAI 实例，连接池复用
_client_instance: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    """获取共享 AsyncOpenAI 实例（懒初始化，连接池复用）。

    测试时可通过 _reset_client() 重置后注入 mock。
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=60,
            max_retries=0,  # 重试由下方循环管理
        )
    return _client_instance


def _reset_client() -> None:
    """重置共享客户端（仅供测试使用）。"""
    global _client_instance
    _client_instance = None


async def aclose() -> None:
    """关闭共享客户端（供 FastAPI lifespan shutdown 调用）。

    幂等：客户端未创建或已关闭时直接返回。
    """
    global _client_instance
    if _client_instance is not None:
        await _client_instance.close()
        _client_instance = None


async def chat(
    messages: list[dict],
    temperature: float = 0.3,
    response_format: dict | None = None,
    json_schema: dict | None = None,
) -> str:
    """调用大模型对话接口。

    Args:
        messages: 消息列表，格式同 OpenAI：
            [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        temperature: 采样温度，默认 0.3。
        response_format: 结构化输出格式，如 {"type": "json_object"}。
        json_schema: JSON Schema 格式，如 {"type": "object", "properties": {"key": {"type": "string"}}}}。

    Returns:
        assistant 回复文本。

    Raises:
        LLMClientError: 网络错误、HTTP 非 2xx 或响应解析失败。
    """
    last_exc = None
    for attempt in range(settings.llm_max_retries + 1):
        try:
            client = _get_client()
            kwargs: dict = {
                "model": settings.llm_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": settings.llm_max_tokens,
                "frequency_penalty": settings.llm_frequency_penalty,
            }
            if json_schema:
                kwargs["response_format"] = {
                    "type": "json_schema",
                    "json_schema": json_schema,
                }
            elif response_format:
                kwargs["response_format"] = response_format

            response = await client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            if not content or not content.strip():
                raise LLMClientError(
                    "大模型返回空内容（content 为空），模型可能陷入推理循环"
                )
            return content

        except RateLimitError as exc:
            last_exc = exc
            if attempt < settings.llm_max_retries:
                await asyncio.sleep(2**attempt)
                continue
            raise LLMClientError(
                f"大模型接口限流，重试耗尽：{exc}"
            ) from exc

        except APITimeoutError as exc:
            last_exc = exc
            if attempt < settings.llm_max_retries:
                await asyncio.sleep(2**attempt)
                continue
            raise LLMClientError(
                f"大模型接口超时，重试耗尽：{exc}"
            ) from exc

        except APIConnectionError as exc:
            raise LLMClientError(
                f"大模型接口连接失败：{exc}"
            ) from exc

        except APIError as exc:
            raise LLMClientError(
                f"大模型接口返回错误：{exc}"
            ) from exc

    raise LLMClientError(f"大模型接口重试耗尽：{last_exc}")


async def embed(texts: list[str]) -> list[list[float]]:
    """调用 embedding 接口。

    Args:
        texts: 待向量化文本列表。

    Returns:
        每个文本对应的向量，顺序与入参一致。

    Raises:
        LLMClientError: 网络错误、HTTP 非 2xx 或响应解析失败。
    """
    last_exc = None
    for attempt in range(settings.llm_max_retries + 1):
        try:
            client = _get_client()
            response = await client.embeddings.create(
                model=settings.llm_embed_model,
                input=texts,
            )
            sorted_data = sorted(response.data, key=lambda item: item.index)
            return [item.embedding for item in sorted_data]

        except RateLimitError as exc:
            last_exc = exc
            if attempt < settings.llm_max_retries:
                await asyncio.sleep(2**attempt)
                continue
            raise LLMClientError(
                f"embedding 接口限流，重试耗尽：{exc}"
            ) from exc

        except APITimeoutError as exc:
            last_exc = exc
            if attempt < settings.llm_max_retries:
                await asyncio.sleep(2**attempt)
                continue
            raise LLMClientError(
                f"embedding 接口超时，重试耗尽：{exc}"
            ) from exc

        except APIConnectionError as exc:
            raise LLMClientError(
                f"embedding 接口连接失败：{exc}"
            ) from exc

        except APIError as exc:
            raise LLMClientError(
                f"embedding 接口返回错误：{exc}"
            ) from exc

    raise LLMClientError(f"embedding 接口重试耗尽：{last_exc}")
