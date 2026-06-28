import importlib.util
import sys
from pathlib import Path

# 将 python-agents/ 加入 sys.path，使 shared 包可被测试导入
sys.path.insert(0, str(Path(__file__).parent.parent))


def _register_kebab_packages():
    """让 agent-knowledge / agent-maintenance 等连字符目录能被 import 为下划线名。

    Python 包名不允许连字符，但项目目录用 kebab-case（AGENTS.md §3.2）。
    这里通过 importlib 把 agent-knowledge 注册为 agent_knowledge 模块，
    使测试中 `from agent_knowledge.rag_chain import ...` 可用。
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
