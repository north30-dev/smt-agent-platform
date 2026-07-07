"""文本处理工具函数。

供 agent-scheduler / agent-quality / agent-maintenance 共享的文本截断与 JSON 提取能力。
"""

import re

_TRUNCATE_SUFFIX = "...(截断)"


def truncate(text: str, max_chars: int) -> str:
    """截断文本以避免 prompt 过长，保证返回长度不超过 max_chars。"""
    if len(text) <= max_chars:
        return text
    if max_chars <= len(_TRUNCATE_SUFFIX):
        return text[:max_chars]
    return text[: max_chars - len(_TRUNCATE_SUFFIX)] + _TRUNCATE_SUFFIX


def extract_json_block(text: str) -> str | None:
    """从 markdown 代码块或裸 JSON 中提取 JSON 文本。

    优先匹配带 json 语言标识的围栏块，取最后一个有效 JSON 代码块
    （LLM 常先给示例再给正式输出）；fallback 用正则捕获最外层 {...} 或 [...]。
    """
    pattern = r"```(?:json|JSON)?\s*\n(.*?)\n\s*```"
    matches = re.findall(pattern, text, re.DOTALL)
    if matches:
        for candidate in reversed(matches):
            stripped = candidate.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                return stripped
    obj_match = re.search(r"\{.*\}", text, re.DOTALL)
    if obj_match:
        return obj_match.group(0)
    arr_match = re.search(r"\[.*\]", text, re.DOTALL)
    if arr_match:
        return arr_match.group(0)
    return None
