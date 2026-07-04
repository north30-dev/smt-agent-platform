"""shared.llm_client 单元测试。

使用 monkeypatch 替换 shared.llm_client.settings 与共享 AsyncClient，
不依赖真实大模型服务。

P0 B1：llm_client.chat/embed 已改 async，测试同步改 async def + AsyncMock。
M1+m1：llm_client 改用共享 AsyncClient + tenacity 重试，测试适配新模式。
"""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from shared import llm_client
from shared.llm_client import LLMClientError, chat, embed


class _FakeResponse:
    """轻量假响应，模拟 httpx.Response 的必要接口。"""

    def __init__(self, status_code: int, json_data: dict):
        self.status_code = status_code
        self._json = json_data
        self.text = str(json_data)

    def json(self) -> dict:
        return self._json


def _patch_settings(monkeypatch, **kwargs) -> MagicMock:
    """替换 llm_client.settings 为可控 mock。"""
    fake = MagicMock()
    fake.llm_api_key = kwargs.get("llm_api_key", "test-key")
    fake.llm_base_url = kwargs.get("llm_base_url", "https://api.example.com/v1")
    fake.llm_model = kwargs.get("llm_model", "qwen-plus")
    fake.llm_embed_model = kwargs.get("llm_embed_model", "text-embedding-v2")
    fake.llm_max_retries = kwargs.get("llm_max_retries", 3)
    fake.llm_retry_backoff = kwargs.get("llm_retry_backoff", 1.0)
    fake.http_max_connections = kwargs.get("http_max_connections", 100)
    monkeypatch.setattr(llm_client, "settings", fake)
    return fake


def _patch_shared_client(monkeypatch, response) -> MagicMock:
    """替换 llm_client._get_client() 返回共享 mock 客户端。"""
    fake_client = MagicMock()
    fake_client.post = AsyncMock(return_value=response)
    monkeypatch.setattr(llm_client, "_get_client", lambda: fake_client)
    return fake_client


async def test_chat_success(monkeypatch):
    """chat 成功返回 assistant 文本，且请求 URL 正确。"""
    _patch_settings(monkeypatch)
    fake_resp = _FakeResponse(200, {"choices": [{"message": {"content": "hello"}}]})
    fake_client = _patch_shared_client(monkeypatch, fake_resp)

    result = await chat([{"role": "user", "content": "hi"}])

    assert result == "hello"
    fake_client.post.assert_called_once()
    posted_url = fake_client.post.call_args.args[0]
    assert posted_url == "https://api.example.com/v1/chat/completions"


async def test_chat_http_error(monkeypatch):
    """HTTP 4xx（非 429）应抛 LLMClientError，不重试。"""
    _patch_settings(monkeypatch)
    fake_resp = _FakeResponse(400, {"error": "bad request"})
    _patch_shared_client(monkeypatch, fake_resp)

    with pytest.raises(LLMClientError):
        await chat([{"role": "user", "content": "hi"}])


async def test_chat_retryable_5xx(monkeypatch):
    """HTTP 500 应重试，最终抛 LLMClientError（_RetryableHTTPError 被转换为重试）。"""
    _patch_settings(monkeypatch, llm_max_retries=1)
    fake_resp = _FakeResponse(500, {"error": "boom"})
    fake_client = _patch_shared_client(monkeypatch, fake_resp)

    with pytest.raises(llm_client._RetryableHTTPError):
        await chat([{"role": "user", "content": "hi"}])

    assert fake_client.post.call_count == 2  # 1 initial + 1 retry


async def test_embed_success(monkeypatch):
    """embed 按 index 排序返回向量，且请求 URL 正确。"""
    _patch_settings(monkeypatch)
    fake_resp = _FakeResponse(
        200,
        {
            "data": [
                {"index": 1, "embedding": [0.1, 0.2]},
                {"index": 0, "embedding": [0.3, 0.4]},
            ]
        },
    )
    fake_client = _patch_shared_client(monkeypatch, fake_resp)

    result = await embed(["a", "b"])

    assert result == [[0.3, 0.4], [0.1, 0.2]]
    posted_url = fake_client.post.call_args.args[0]
    assert posted_url == "https://api.example.com/v1/embeddings"


async def test_get_client_creates_shared_instance(monkeypatch):
    """_get_client 应返回共享 AsyncClient 实例（连接池复用）。"""
    _patch_settings(monkeypatch, http_max_connections=50)
    llm_client._reset_client()

    client1 = llm_client._get_client()
    client2 = llm_client._get_client()

    assert client1 is client2
    assert isinstance(client1, httpx.AsyncClient)

    llm_client._reset_client()
