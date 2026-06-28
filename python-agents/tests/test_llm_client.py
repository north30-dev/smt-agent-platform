"""shared.llm_client 单元测试。

使用 monkeypatch 替换 shared.llm_client.settings 与 httpx.Client，
不依赖真实大模型服务。
"""

from unittest.mock import MagicMock

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
    monkeypatch.setattr(llm_client, "settings", fake)
    return fake


def _patch_httpx(monkeypatch, response) -> MagicMock:
    """替换 httpx.Client 为返回固定响应的假客户端（上下文管理器协议）。"""
    fake_client = MagicMock()
    fake_client.post.return_value = response
    fake_client.__enter__.return_value = fake_client
    fake_client.__exit__.return_value = False
    monkeypatch.setattr(llm_client.httpx, "Client", lambda *a, **k: fake_client)
    return fake_client


def test_chat_success(monkeypatch):
    """chat 成功返回 assistant 文本，且请求 URL 正确。"""
    _patch_settings(monkeypatch)
    fake_resp = _FakeResponse(200, {"choices": [{"message": {"content": "hello"}}]})
    fake_client = _patch_httpx(monkeypatch, fake_resp)

    result = chat([{"role": "user", "content": "hi"}])

    assert result == "hello"
    fake_client.post.assert_called_once()
    posted_url = fake_client.post.call_args.args[0]
    assert posted_url == "https://api.example.com/v1/chat/completions"


def test_chat_http_error(monkeypatch):
    """HTTP 5xx 应抛 LLMClientError。"""
    _patch_settings(monkeypatch)
    fake_resp = _FakeResponse(500, {"error": "boom"})
    _patch_httpx(monkeypatch, fake_resp)

    with pytest.raises(LLMClientError):
        chat([{"role": "user", "content": "hi"}])


def test_embed_success(monkeypatch):
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
    fake_client = _patch_httpx(monkeypatch, fake_resp)

    result = embed(["a", "b"])

    assert result == [[0.3, 0.4], [0.1, 0.2]]
    posted_url = fake_client.post.call_args.args[0]
    assert posted_url == "https://api.example.com/v1/embeddings"
