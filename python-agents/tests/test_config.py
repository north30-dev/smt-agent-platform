"""shared.config 配置加载测试。

补齐 phase2 报告 B-11 盲区：config.py 的 pydantic-settings 加载逻辑、
.env 缺失字段时的降级行为未测试。

验证：
1. LLM_API_KEY 缺失时 settings.llm_api_key 为默认空字符串（不抛异常）
2. MILVUS_PORT 非数字时 pydantic 抛 ValidationError
"""

import pytest
from pydantic import ValidationError

from shared.config import Settings


def test_llm_api_key_defaults_to_empty_string(monkeypatch):
    """LLM_API_KEY 缺失时 settings.llm_api_key 应为默认空字符串。

    守护 config.py 第 15 行 `llm_api_key: str = ""` 默认值行为。
    """
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    settings = Settings()
    assert settings.llm_api_key == ""


def test_milvus_port_non_numeric_raises_validation_error(monkeypatch):
    """MILVUS_PORT 非数字时 pydantic 应抛 ValidationError。

    守护 config.py 第 22 行 `milvus_port: int = 19530` 类型校验。
    """
    monkeypatch.setenv("MILVUS_PORT", "not-a-port")
    with pytest.raises(ValidationError):
        Settings()


def test_milvus_port_numeric_string_coerced(monkeypatch):
    """MILVUS_PORT 数字字符串应被 pydantic 自动转换为 int。"""
    monkeypatch.setenv("MILVUS_PORT", "19531")
    settings = Settings()
    assert settings.milvus_port == 19531
    assert isinstance(settings.milvus_port, int)
