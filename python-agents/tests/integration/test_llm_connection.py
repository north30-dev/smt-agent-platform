"""大模型连接集成测试。

验证通过 API_KEY 能否正常连接大模型并获取响应。
标记 @pytest.mark.integration，需用 `pytest -m integration` 显式触发。

环境受限时（API_KEY 缺失 / 网络不通）自动 skip。
"""

import pytest

from shared.config import settings
from shared.llm_client import LLMClientError, _reset_client, chat, embed


@pytest.fixture(autouse=True)
def _skip_if_no_api_key():
    """API_KEY 缺失时自动 skip。"""
    if not settings.llm_api_key:
        pytest.skip("LLM_API_KEY 未配置，跳过大模型连接测试")


@pytest.fixture(autouse=True)
def _reset_llm_client():
    """每个测试前重置共享客户端，避免事件循环问题。"""
    _reset_client()
    yield
    _reset_client()


@pytest.mark.integration
@pytest.mark.anyio
async def test_llm_chat_completion():
    """验证大模型 Chat Completion 接口可用。"""
    response = await chat(
        messages=[{"role": "user", "content": "回答：1+1等于几？只回答数字。"}],
        temperature=0,
    )
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0


@pytest.mark.integration
@pytest.mark.anyio
async def test_llm_embedding():
    """验证大模型 Embedding 接口可用。"""
    embeddings = await embed(texts=["测试文本"])
    assert embeddings is not None
    assert len(embeddings) > 0
    assert isinstance(embeddings[0], list)
    # 通义 embedding 维度通常是 1536
    assert len(embeddings[0]) > 100
