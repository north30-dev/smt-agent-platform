"""故障诊断模块。

串联设备信息查询、相似案例检索、大模型对话，
对上暴露案例录入与故障诊断两个原子能力。
错误不在本模块捕获，统一交由 main.py 异常处理器兜底。
"""

import json
from pathlib import Path
from uuid import uuid4

import yaml

from shared import llm_client, vector_store

from .device_client import DeviceServiceUnavailable, device_client

# 故障案例 collection 名
COLLECTION = "smt_fault_cases"

# Prompt 模板文件
_PROMPT_FILE = Path(__file__).parent.parent / "shared" / "prompts" / "system_prompt.yaml"

# 模块级懒初始化标志，避免每次写案例都重复建表建索引
_initialized = False


def create_case(device_type: str, symptom: str, root_cause: str, solution: str) -> str:
    """录入故障案例：拼案例文本 → embed → insert。

    Args:
        device_type: 设备类型。
        symptom: 故障现象。
        root_cause: 根因。
        solution: 解决方案。

    Returns:
        生成的 case_id。
    """
    global _initialized

    case_id = f"case-{uuid4().hex[:8]}"
    case_text = (
        f"设备类型：{device_type}\n"
        f"症状：{symptom}\n"
        f"根因：{root_cause}\n"
        f"解决方案：{solution}"
    )
    chunks = [case_text]

    vectors = llm_client.embed(chunks)

    if not _initialized:
        vector_store.init_collections(len(vectors[0]))
        _initialized = True

    vector_store.insert(COLLECTION, case_id, chunks, vectors)
    return case_id


def diagnose(device_id: int, symptom: str) -> dict:
    """故障诊断流程。

    1. 获取设备信息
    2. 检索相似历史案例
    3. 调用大模型生成根因假设与维修建议
    4. 解析 LLM 输出，失败时降级

    Args:
        device_id: 设备 ID。
        symptom: 故障现象描述。

    Returns:
        {root_causes, repair_suggestions, similar_cases}
    """
    # 1. 获取设备信息
    device_info = device_client.get_device(device_id)

    # 2. 检索相似历史案例
    query_vector = llm_client.embed([symptom])[0]
    sources = vector_store.search(COLLECTION, query_vector, top_k=3)
    similar_cases = _parse_similar_cases(sources)

    # 3. 拼 prompt 并调用大模型
    system_prompt, user_template = _load_prompts()
    similar_cases_text = _format_similar_cases_text(similar_cases)
    user_content = user_template.format(
        device_info=_format_device_info(device_info),
        symptom=symptom,
        similar_cases=similar_cases_text,
    )
    # 追加 JSON 输出约束
    user_content = (
        user_content
        + "\n\n请以 JSON 格式输出，结构为："
        '{"root_causes": ["根因1", "根因2"], "repair_suggestions": ["建议1", "建议2"]}'
    )

    raw_text = llm_client.chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
    )

    # 4. 解析 LLM 输出
    root_causes, repair_suggestions = _parse_llm_output(raw_text)

    return {
        "root_causes": root_causes,
        "repair_suggestions": repair_suggestions,
        "similar_cases": similar_cases,
    }


def _load_prompts() -> tuple[str, str]:
    """读取 system_prompt.yaml 中的 maintenance.system 与 diagnose_template。"""
    with _PROMPT_FILE.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    maintenance = data["maintenance"]
    return maintenance["system"], maintenance["diagnose_template"]


def _format_device_info(device_info: dict) -> str:
    """将设备信息 dict 格式化为简短文本。"""
    if not device_info:
        return "（无设备信息）"
    parts = []
    for key in ("deviceCode", "deviceName", "deviceType", "productionLine", "status"):
        if key in device_info and device_info[key] is not None:
            parts.append(f"{key}={device_info[key]}")
    return ", ".join(parts) if parts else str(device_info)


def _parse_similar_cases(sources: list[dict]) -> list[dict]:
    """将向量检索结果解析为 SimilarCase 结构。

    案例文本按行存储，格式：
        设备类型：xxx
        症状：xxx
        根因：xxx
        解决方案：xxx
    解析失败时将整段文本作为 symptom。
    """
    cases: list[dict] = []
    for src in sources:
        content = src.get("content") or ""
        case_id = src.get("doc_id") or ""
        score = float(src.get("score") or 0.0)

        symptom = ""
        root_cause = ""
        solution = ""
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("症状：") or line.startswith("症状:"):
                symptom = line.split("：", 1)[-1].split(":", 1)[-1]
            elif line.startswith("根因：") or line.startswith("根因:"):
                root_cause = line.split("：", 1)[-1].split(":", 1)[-1]
            elif line.startswith("解决方案：") or line.startswith("解决方案:"):
                solution = line.split("：", 1)[-1].split(":", 1)[-1]

        if not symptom:
            symptom = content.strip()

        cases.append(
            {
                "case_id": case_id,
                "symptom": symptom,
                "root_cause": root_cause,
                "solution": solution,
                "score": score,
            }
        )
    return cases


def _format_similar_cases_text(cases: list[dict]) -> str:
    """将相似案例列表格式化为大模型可读文本。"""
    if not cases:
        return "（暂无相似历史案例）"
    blocks = []
    for i, c in enumerate(cases, start=1):
        blocks.append(
            f"[案例{i}] id={c['case_id']} score={c['score']:.3f}\n"
            f"  症状：{c['symptom']}\n"
            f"  根因：{c['root_cause']}\n"
            f"  解决方案：{c['solution']}"
        )
    return "\n".join(blocks)


def _parse_llm_output(raw_text: str) -> tuple[list[str], list[str]]:
    """解析 LLM 输出为 (root_causes, repair_suggestions)。

    期望 LLM 输出 JSON：{"root_causes": [...], "repair_suggestions": [...]}
    解析失败时降级：root_causes=[raw_text]，repair_suggestions=[]
    """
    text = raw_text.strip()
    # 尝试直接解析
    try:
        data = json.loads(text)
        return _extract_lists(data)
    except (ValueError, TypeError):
        pass

    # 尝试从 ```json ... ``` 代码块中提取
    code = _extract_json_block(text)
    if code is not None:
        try:
            data = json.loads(code)
            return _extract_lists(data)
        except (ValueError, TypeError):
            pass

    # 降级：整段文本作为根因
    return [raw_text], []


def _extract_json_block(text: str) -> str | None:
    """从 markdown 代码块中提取 JSON 文本，找不到返回 None。"""
    fence = "```"
    start = text.find(fence)
    if start == -1:
        return None
    rest = text[start + len(fence):]
    # 跳过可选的 "json" 语言标识
    if rest[:4].lower().startswith("json"):
        rest = rest[4:]
    end = rest.find(fence)
    if end == -1:
        return None
    return rest[:end].strip()


def _extract_lists(data: dict) -> tuple[list[str], list[str]]:
    """从 dict 中提取 root_causes 与 repair_suggestions，缺失补空列表。"""
    root_causes = data.get("root_causes") or []
    repair_suggestions = data.get("repair_suggestions") or []
    if not isinstance(root_causes, list):
        root_causes = [str(root_causes)]
    if not isinstance(repair_suggestions, list):
        repair_suggestions = [str(repair_suggestions)]
    return [str(x) for x in root_causes], [str(x) for x in repair_suggestions]
