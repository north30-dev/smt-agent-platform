import importlib.util
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# 将 python-agents/ 加入 sys.path，使 shared 包可被测试导入
sys.path.insert(0, str(Path(__file__).parent.parent))


def _register_kebab_packages():
    """让 agent-knowledge / agent-maintenance 等连字符目录能被 import 为下划线名。

    Python 包名不允许连字符，但项目目录用 kebab-case（AGENTS.md §3.2）。
    这里通过 importlib 把 agent-knowledge 注册为 agent_knowledge 模块，
    使测试中 `from agent_knowledge.rag_chain import ...` 可用。

    Gap: 当前仅注册 agent-knowledge/agent-maintenance 两个包，
    新增 Agent 时需手动追加到 PACKAGES 列表。
    未来考虑改用 setuptools entry_points 或 namespace package 自动发现。
    """
    root = Path(__file__).parent.parent
    for kebab in ["agent-knowledge", "agent-maintenance"]:
        underscore = kebab.replace("-", "_")
        if underscore in sys.modules:
            continue
        pkg_path = root / kebab
        if not (pkg_path.is_dir() and (pkg_path / "__init__.py").exists()):
            continue
        spec = importlib.util.spec_from_file_location(
            underscore,
            pkg_path / "__init__.py",
            submodule_search_locations=[str(pkg_path)],
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[underscore] = module
        spec.loader.exec_module(module)


_register_kebab_packages()


@pytest.fixture
def mock_device_client():
    """共享 mock DeviceClient，避免各测试重复构造。

    返回 MagicMock，get_device/list_datapoints/get_device_data 为 AsyncMock。
    各测试可按需覆盖返回值。
    """
    fake = MagicMock()
    fake.get_device = AsyncMock(return_value={"id": 1, "deviceCode": "D001"})
    fake.list_datapoints = AsyncMock(return_value=[])
    fake.get_device_data = AsyncMock(return_value=[])
    return fake


@pytest.fixture
def mock_llm_chat():
    """共享 mock llm_client.chat，返回即时响应。

    各测试可按需 monkeypatch 覆盖返回值或 side_effect。
    """

    async def _fake_chat(messages, temperature=0.3):
        return "mocked LLM response"

    return _fake_chat
