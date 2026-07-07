"""质量根因分析模块。

串联设备信息查询、相似案例检索、大模型对话，
对上暴露案例录入与根因分析两个原子能力。
错误不在本模块捕获，统一交由 main.py 异常处理器兜底。
"""

import asyncio
import json
import re
import threading
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

import yaml

from shared import llm_client, vector_store

# 复用 agent-maintenance 已有的 device-service HTTP 客户端
from .device_client import DeviceServiceUnavailable, device_client

# 质量案例 collection 名（与 shared.vector_store.COLLECTIONS 对齐）
COLLECTION = "smt_quality_cases"

# Prompt 模板文件
_PROMPT_FILE = Path(__file__).parent.parent / "shared" / "prompts" / "system_prompt.yaml"

# 模块级懒初始化标志与保护锁（防止多线程并发 check-then-set 竞态）
_initialized = False
_init_lock = threading.Lock()


async def create_case(
    defect_type: str,
    description: str,
    root_cause: str,
    corrective_action: str,
) -> str:
    """录入质量案例：拼案例文本 → embed → insert。

    Args:
        defect_type: 缺陷类型（如 AOI_TOMBSTONE）。
        description: 缺陷描述。
        root_cause: 根因。
        corrective_action: 纠正措施。

    Returns:
        生成的 case_id（qcase- 前缀）。
    """
    global _initialized

    case_id = f"qcase-{uuid4().hex[:8]}"
    case_text = (
        f"缺陷类型：{defect_type}\n"
        f"描述：{description}\n"
        f"根因：{root_cause}\n"
        f"纠正措施：{corrective_action}"
    )
    chunks = [case_text]

    vectors = await llm_client.embed(chunks)

    if not _initialized:
        with _init_lock:
            if not _initialized:
                await asyncio.to_thread(vector_store.init_collections, len(vectors[0]))
                _initialized = True

    await asyncio.to_thread(vector_store.insert, COLLECTION, case_id, chunks, vectors)
    return case_id


async def analyze(device_id: int, defect_description: str) -> dict:
    """质量根因分析主流程。

    1. 获取设备信息
    2. 检索相似历史案例
    3. 调用大模型按"人/机/料/法/环"五要素生成根因与纠正措施
    4. 解析 LLM 输出，失败时降级

    Args:
        device_id: 设备 ID。
        defect_description: 缺陷描述。

    Returns:
        {device_id, root_causes, corrective_actions, similar_cases}

    Raises:
        DeviceServiceUnavailable: device-service 不可达时透传给上层。
    """
    # 1. 获取设备信息
    device_info = await device_client.get_device(device_id)

    # 2. 检索相似历史案例
    query_vector = (await llm_client.embed([defect_description]))[0]
    sources = await asyncio.to_thread(vector_store.search, COLLECTION, query_vector, 3)
    similar_cases = _parse_similar_cases(sources)

    # 3. 拼 prompt 并调用大模型（root_cause_template 已含 JSON 输出约束）
    # 注意：模板末尾含 JSON 示例（{"root_causes": ...}），不能用 str.format()
    # 否则字面 { } 会被当作占位符解析抛 KeyError。改用 str.replace() 安全替换。
    system_prompt, user_template = _load_prompts()
    similar_cases_text = _format_similar_cases_text(similar_cases)
    user_content = (
        user_template.replace("{device_info}", _format_device_info(device_info))
        .replace("{defect_description}", defect_description)
        .replace("{similar_cases}", similar_cases_text)
    )

    raw_text = await llm_client.chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
    )

    # 4. 解析 LLM 输出
    root_causes, corrective_actions = _parse_llm_output(raw_text)

    return {
        "device_id": device_id,
        "root_causes": root_causes,
        "corrective_actions": corrective_actions,
        "similar_cases": similar_cases,
    }


@lru_cache(maxsize=1)
def _load_prompts() -> tuple[str, str]:
    """读取 system_prompt.yaml 中的 quality.system 与 root_cause_template。

    Prompt 文件运行期不变，用 lru_cache 避免每次请求重复读盘。
    """
    with _PROMPT_FILE.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    quality = data["quality"]
    return quality["system"], quality["root_cause_template"]


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
        缺陷类型：xxx
        描述：xxx
        根因：xxx
        纠正措施：xxx
    解析失败时将整段文本作为 description。
    """
    cases: list[dict] = []
    for src in sources:
        content = src.get("content") or ""
        case_id = src.get("doc_id") or ""
        score = float(src.get("score") or 0.0)

        description = ""
        root_cause = ""
        corrective_action = ""
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("描述：") or line.startswith("描述:"):
                description = line.split("：", 1)[-1].split(":", 1)[-1]
            elif line.startswith("根因：") or line.startswith("根因:"):
                root_cause = line.split("：", 1)[-1].split(":", 1)[-1]
            elif line.startswith("纠正措施：") or line.startswith("纠正措施:"):
                corrective_action = line.split("：", 1)[-1].split(":", 1)[-1]

        if not description:
            description = content.strip()

        cases.append(
            {
                "case_id": case_id,
                "description": description,
                "root_cause": root_cause,
                "corrective_action": corrective_action,
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
            f"  描述：{c['description']}\n"
            f"  根因：{c['root_cause']}\n"
            f"  纠正措施：{c['corrective_action']}"
        )
    return "\n".join(blocks)


def _parse_llm_output(raw_text: str) -> tuple[list[dict], list[str]]:
    """解析 LLM 输出为 (root_causes, corrective_actions)。

    期望 LLM 输出 JSON：
        {"root_causes": [{"category": "机", "cause": "..."}],
         "corrective_actions": ["措施1", "措施2"]}

    解析失败时降级：
        root_causes=[{"category":"未知","cause":raw_text}]，corrective_actions=[]
    """
    text = raw_text.strip()
    # 尝试直接解析
    try:
        data = json.loads(text)
        return _extract_fields(data)
    except (ValueError, TypeError):
        pass

    # 尝试从 ```json ... ``` 代码块中提取
    code = _extract_json_block(text)
    if code is not None:
        try:
            data = json.loads(code)
            return _extract_fields(data)
        except (ValueError, TypeError):
            pass

    # 降级：整段文本作为根因
    return [{"category": "未知", "cause": raw_text}], []


def _extract_json_block(text: str) -> str | None:
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


def _extract_fields(data: dict) -> tuple[list[dict], list[str]]:
    """从 dict 中提取 root_causes 与 corrective_actions，缺失补空。"""
    raw_root_causes = data.get("root_causes") or []
    corrective_actions = data.get("corrective_actions") or []

    root_causes: list[dict] = []
    if isinstance(raw_root_causes, list):
        for item in raw_root_causes:
            if isinstance(item, dict):
                root_causes.append(
                    {
                        "category": str(item.get("category") or "未知"),
                        "cause": str(item.get("cause") or ""),
                    }
                )
            else:
                root_causes.append({"category": "未知", "cause": str(item)})
    elif isinstance(raw_root_causes, dict):
        # LLM 偶发返回单个对象而非列表
        root_causes.append(
            {
                "category": str(raw_root_causes.get("category") or "未知"),
                "cause": str(raw_root_causes.get("cause") or ""),
            }
        )
    else:
        root_causes.append({"category": "未知", "cause": str(raw_root_causes)})

    if not isinstance(corrective_actions, list):
        corrective_actions = [str(corrective_actions)]
    else:
        corrective_actions = [str(x) for x in corrective_actions]

    return root_causes, corrective_actions
