"""shared.llm_client 单元测试。

使用 monkeypatch 替换 shared.llm_client.settings 与共享 AsyncOpenAI 实例，
不依赖真实大模型服务。

改用 openai.AsyncOpenAI 后，测试适配新的 mock 模式。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from shared import llm_client
from shared.llm_client import LLMClientError, chat, embed


def _patch_settings(monkeypatch, **kwargs) -> MagicMock:
    """替换 llm_client.settings 为可控 mock。"""
    fake = MagicMock()
    fake.llm_api_key = kwargs.get("llm_api_key", "test-key")
    fake.llm_base_url = kwargs.get("llm_base_url", "https://api.example.com/v1")
    fake.llm_model = kwargs.get("llm_model", "qwen-plus")
    fake.llm_embed_model = kwargs.get("llm_embed_model", "text-embedding-v2")
    fake.llm_max_retries = kwargs.get("llm_max_retries", 3)
    fake.llm_retry_backoff = kwargs.get("llm_retry_backoff", 1.0)
    fake.llm_max_tokens = kwargs.get("llm_max_tokens", 4096)
    fake.llm_frequency_penalty = kwargs.get("llm_frequency_penalty", 0.5)
    monkeypatch.setattr(llm_client, "settings", fake)
    return fake


def _make_chat_response(content: str) -> MagicMock:
    """构造 OpenAI chat completion 响应 mock。"""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    return response


def _make_embed_response(embeddings: list[list[float]]) -> MagicMock:
    """构造 OpenAI embedding 响应 mock。"""
    response = MagicMock()
    response.data = [
        MagicMock(index=i, embedding=emb) for i, emb in enumerate(embeddings)
    ]
    return response


def _patch_client(monkeypatch, chat_response=None, embed_response=None):
    """替换 llm_client._get_client() 返回共享 mock 客户端。"""
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=chat_response)
    fake_client.embeddings.create = AsyncMock(return_value=embed_response)
    fake_client.close = AsyncMock()
    monkeypatch.setattr(llm_client, "_get_client", lambda: fake_client)
    return fake_client


async def test_chat_success(monkeypatch):
    """chat 成功返回 assistant 文本。"""
    _patch_settings(monkeypatch)
    fake_resp = _make_chat_response("hello")
    _patch_client(monkeypatch, chat_response=fake_resp)

    result = await chat([{"role": "user", "content": "hi"}])

    assert result == "hello"


async def test_chat_empty_content_raises(monkeypatch):
    """chat 返回空内容应抛 LLMClientError。"""
    _patch_settings(monkeypatch)
    fake_resp = _make_chat_response("")
    _patch_client(monkeypatch, chat_response=fake_resp)

    with pytest.raises(LLMClientError, match="空内容"):
        await chat([{"role": "user", "content": "hi"}])


async def test_chat_with_response_format(monkeypatch):
    """chat 传入 response_format 时应正确传递给 SDK。"""
    _patch_settings(monkeypatch)
    fake_resp = _make_chat_response('{"key": "value"}')
    fake_client = _patch_client(monkeypatch, chat_response=fake_resp)

    result = await chat(
        [{"role": "user", "content": "hi"}],
        response_format={"type": "json_object"},
    )

    assert result == '{"key": "value"}'
    call_kwargs = fake_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["response_format"] == {"type": "json_object"}

    # 测试 json_schema 参数
    result = await chat(
        [{"role": "user", "content": "hi"}],
        json_schema={"type": "object", "properties": {"key": {"type": "string"}}},
    )

    assert result == '{"key": "value"}'
    call_kwargs = fake_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["response_format"] == {
        "type": "json_schema",
        "json_schema": {"type": "object", "properties": {"key": {"type": "string"}}},
    }


async def test_embed_success(monkeypatch):
    """embed 按 index 排序返回向量。"""
    _patch_settings(monkeypatch)
    fake_resp = _make_embed_response([[0.3, 0.4], [0.1, 0.2]])
    _patch_client(monkeypatch, embed_response=fake_resp)

    result = await embed(["a", "b"])

    assert result == [[0.3, 0.4], [0.1, 0.2]]


async def test_get_client_creates_shared_instance(monkeypatch):
    """_get_client 应返回共享 AsyncOpenAI 实例（连接池复用）。"""
    _patch_settings(monkeypatch)
    llm_client._reset_client()

    client1 = llm_client._get_client()
    client2 = llm_client._get_client()

    assert client1 is client2

    llm_client._reset_client()
