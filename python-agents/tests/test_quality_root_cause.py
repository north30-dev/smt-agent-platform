"""agent_quality.root_cause 单元测试。

使用 monkeypatch 替换 root_cause 模块内已 import 的 shared 引用
（llm_client / vector_store）与 device_client，不依赖真实 Milvus、
大模型与 Java device-service。

- llm_client.embed/chat → AsyncMock（被 await 调用）
- device_client.get_device → AsyncMock（被 await 调用）
- vector_store.insert/init_collections/search → MagicMock（被 asyncio.to_thread 包装为同步）
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from shared.device_client import DeviceServiceUnavailable
from agent_quality.root_cause import COLLECTION, analyze, create_case


async def test_create_case(monkeypatch):
    """录入案例应串联 embed → init_collections → insert，并返回 qcase- 前缀 ID。"""
    # 重置懒初始化标志，保证本用例触发 init_collections
    monkeypatch.setattr("agent_quality.root_cause._initialized", False)

    mock_llm = MagicMock()
    mock_llm.embed = AsyncMock(return_value=[[0.1, 0.2]])
    monkeypatch.setattr("agent_quality.root_cause.llm_client", mock_llm)

    mock_vs = MagicMock()
    mock_vs.insert.return_value = 1
    monkeypatch.setattr("agent_quality.root_cause.vector_store", mock_vs)

    case_id = await create_case(
        "AOI_TOMBSTONE", "元器件立碑", "炉温曲线偏移", "调整回流焊温区"
    )

    assert case_id.startswith("qcase-")
    assert len(case_id) == len("qcase-") + 8
    mock_llm.embed.assert_called_once()
    mock_vs.init_collections.assert_called_once_with(2)
    mock_vs.insert.assert_called_once()
    # insert 入参：collection, doc_id, chunks, vectors
    args = mock_vs.insert.call_args.args
    assert args[0] == COLLECTION
    assert args[1] == case_id
    assert len(args[2]) == 1
    case_text = args[2][0]
    assert "AOI_TOMBSTONE" in case_text
    assert "元器件立碑" in case_text
    assert "炉温曲线偏移" in case_text
    assert "调整回流焊温区" in case_text


async def test_create_case_skips_init_when_already_initialized(monkeypatch):
    """已初始化时应跳过 init_collections，仅走 embed → insert。"""
    monkeypatch.setattr("agent_quality.root_cause._initialized", True)

    mock_llm = MagicMock()
    mock_llm.embed = AsyncMock(return_value=[[0.1, 0.2]])
    monkeypatch.setattr("agent_quality.root_cause.llm_client", mock_llm)

    mock_vs = MagicMock()
    mock_vs.insert.return_value = 1
    monkeypatch.setattr("agent_quality.root_cause.vector_store", mock_vs)

    case_id = await create_case("X", "y", "z", "w")

    assert case_id.startswith("qcase-")
    mock_vs.init_collections.assert_not_called()
    mock_vs.insert.assert_called_once()


async def test_analyze_success(monkeypatch):
    """分析应串联 get_device → embed → search → chat，并解析 LLM JSON 输出。"""
    mock_device = MagicMock()
    mock_device.get_device = AsyncMock(return_value={"id": 1, "deviceName": "贴片机"})
    monkeypatch.setattr("agent_quality.root_cause.device_client", mock_device)

    mock_llm = MagicMock()
    mock_llm.embed = AsyncMock(return_value=[[0.1, 0.2]])
    mock_llm.chat = AsyncMock(
        return_value=(
            '{"root_causes": [{"category": "机", "cause": "炉温偏移"}], '
            '"corrective_actions": ["调整温区"]}'
        )
    )
    monkeypatch.setattr("agent_quality.root_cause.llm_client", mock_llm)

    mock_vs = MagicMock()
    mock_vs.search.return_value = [
        {
            "doc_id": "q1",
            "chunk_id": 0,
            "content": (
                "缺陷类型：AOI_TOMBSTONE\n"
                "描述：立碑\n"
                "根因：炉温偏移\n"
                "纠正措施：调整温区"
            ),
            "score": 0.9,
        }
    ]
    monkeypatch.setattr("agent_quality.root_cause.vector_store", mock_vs)

    result = await analyze(1, "元器件立碑")

    assert result["device_id"] == 1
    assert len(result["root_causes"]) == 1
    assert result["root_causes"][0]["category"] == "机"
    assert result["root_causes"][0]["cause"] == "炉温偏移"
    assert result["corrective_actions"] == ["调整温区"]
    assert len(result["similar_cases"]) == 1
    case = result["similar_cases"][0]
    assert case["case_id"] == "q1"
    assert case["score"] == 0.9
    assert case["description"] == "立碑"
    assert case["root_cause"] == "炉温偏移"
    assert case["corrective_action"] == "调整温区"

    mock_device.get_device.assert_called_once_with(1)
    mock_llm.embed.assert_called_once_with(["元器件立碑"])
    mock_vs.search.assert_called_once()
    mock_llm.chat.assert_called_once()
    # chat 收到 system + user 两条消息
    messages = mock_llm.chat.call_args.args[0]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    # user 消息应包含缺陷描述与五要素约束
    assert "元器件立碑" in messages[1]["content"]
    assert "root_causes" in messages[1]["content"]


async def test_analyze_empty_case_library(monkeypatch):
    """空案例库时应返回空 similar_cases 与 LLM 给出的 root_causes。"""
    mock_device = MagicMock()
    mock_device.get_device = AsyncMock(return_value={"id": 1, "deviceName": "贴片机"})
    monkeypatch.setattr("agent_quality.root_cause.device_client", mock_device)

    mock_llm = MagicMock()
    mock_llm.embed = AsyncMock(return_value=[[0.1, 0.2]])
    mock_llm.chat = AsyncMock(
        return_value=(
            '{"root_causes": [{"category": "料", "cause": "焊膏过期"}], '
            '"corrective_actions": ["更换焊膏"]}'
        )
    )
    monkeypatch.setattr("agent_quality.root_cause.llm_client", mock_llm)

    mock_vs = MagicMock()
    mock_vs.search.return_value = []
    monkeypatch.setattr("agent_quality.root_cause.vector_store", mock_vs)

    result = await analyze(1, "焊点不良")

    assert result["similar_cases"] == []
    assert len(result["root_causes"]) == 1
    assert result["root_causes"][0]["category"] == "料"
    assert result["corrective_actions"] == ["更换焊膏"]


async def test_analyze_llm_not_json(monkeypatch):
    """LLM 输出非 JSON 时应降级为 root_causes=[{category:未知, cause:raw_text}]。"""
    mock_device = MagicMock()
    mock_device.get_device = AsyncMock(return_value={"id": 1, "deviceName": "贴片机"})
    monkeypatch.setattr("agent_quality.root_cause.device_client", mock_device)

    mock_llm = MagicMock()
    mock_llm.embed = AsyncMock(return_value=[[0.1, 0.2]])
    mock_llm.chat = AsyncMock(return_value="无法解析：疑似炉温问题")
    monkeypatch.setattr("agent_quality.root_cause.llm_client", mock_llm)

    mock_vs = MagicMock()
    mock_vs.search.return_value = []
    monkeypatch.setattr("agent_quality.root_cause.vector_store", mock_vs)

    result = await analyze(1, "立碑")

    assert len(result["root_causes"]) == 1
    assert result["root_causes"][0]["category"] == "未知"
    assert "无法解析" in result["root_causes"][0]["cause"]
    assert result["corrective_actions"] == []


async def test_analyze_llm_markdown_json(monkeypatch):
    """LLM 输出 markdown 代码块包裹的 JSON 时应正确解析。"""
    mock_device = MagicMock()
    mock_device.get_device = AsyncMock(return_value={"id": 1, "deviceName": "贴片机"})
    monkeypatch.setattr("agent_quality.root_cause.device_client", mock_device)

    mock_llm = MagicMock()
    mock_llm.embed = AsyncMock(return_value=[[0.1, 0.2]])
    mock_llm.chat = AsyncMock(
        return_value=(
            "分析结果如下：\n"
            "```json\n"
            '{"root_causes": [{"category": "法", "cause": "钢网清洁不规范"}], '
            '"corrective_actions": ["按 SOP 清洁"]}\n'
            "```\n"
        )
    )
    monkeypatch.setattr("agent_quality.root_cause.llm_client", mock_llm)

    mock_vs = MagicMock()
    mock_vs.search.return_value = []
    monkeypatch.setattr("agent_quality.root_cause.vector_store", mock_vs)

    result = await analyze(1, "桥接")

    assert len(result["root_causes"]) == 1
    assert result["root_causes"][0]["category"] == "法"
    assert result["root_causes"][0]["cause"] == "钢网清洁不规范"
    assert result["corrective_actions"] == ["按 SOP 清洁"]


async def test_analyze_multi_root_causes(monkeypatch):
    """多根因场景应正确解析多元素分类。"""
    mock_device = MagicMock()
    mock_device.get_device = AsyncMock(return_value={"id": 1, "deviceName": "贴片机"})
    monkeypatch.setattr("agent_quality.root_cause.device_client", mock_device)

    mock_llm = MagicMock()
    mock_llm.embed = AsyncMock(return_value=[[0.1, 0.2]])
    mock_llm.chat = AsyncMock(
        return_value=(
            '{"root_causes": ['
            '{"category": "机", "cause": "贴片机吸嘴磨损"},'
            '{"category": "料", "cause": "元件氧化"},'
            '{"category": "法", "cause": "贴装压力设置不当"}'
            '], "corrective_actions": ["更换吸嘴", "更换元件", "校准贴装压力"]}'
        )
    )
    monkeypatch.setattr("agent_quality.root_cause.llm_client", mock_llm)

    mock_vs = MagicMock()
    mock_vs.search.return_value = []
    monkeypatch.setattr("agent_quality.root_cause.vector_store", mock_vs)

    result = await analyze(1, "贴装偏移")

    assert len(result["root_causes"]) == 3
    categories = [rc["category"] for rc in result["root_causes"]]
    assert "机" in categories
    assert "料" in categories
    assert "法" in categories
    assert len(result["corrective_actions"]) == 3


async def test_analyze_device_unavailable(monkeypatch):
    """device-service 不可达时应抛出 DeviceServiceUnavailable。"""
    mock_device = MagicMock()
    mock_device.get_device = AsyncMock(
        side_effect=DeviceServiceUnavailable("connection refused")
    )
    monkeypatch.setattr("agent_quality.root_cause.device_client", mock_device)

    with pytest.raises(DeviceServiceUnavailable):
        await analyze(1, "立碑")


async def test_analyze_similar_case_parse_fallback(monkeypatch):
    """相似案例文本无法按行解析时应将整段文本作为 description。"""
    mock_device = MagicMock()
    mock_device.get_device = AsyncMock(return_value={"id": 1, "deviceName": "贴片机"})
    monkeypatch.setattr("agent_quality.root_cause.device_client", mock_device)

    mock_llm = MagicMock()
    mock_llm.embed = AsyncMock(return_value=[[0.1, 0.2]])
    mock_llm.chat = AsyncMock(
        return_value='{"root_causes": [], "corrective_actions": []}'
    )
    monkeypatch.setattr("agent_quality.root_cause.llm_client", mock_llm)

    mock_vs = MagicMock()
    # 无标准格式行的纯文本
    mock_vs.search.return_value = [
        {"doc_id": "q2", "chunk_id": 0, "content": "一段纯文本无格式", "score": 0.5}
    ]
    monkeypatch.setattr("agent_quality.root_cause.vector_store", mock_vs)

    result = await analyze(1, "缺陷")

    assert len(result["similar_cases"]) == 1
    case = result["similar_cases"][0]
    assert case["case_id"] == "q2"
    assert case["description"] == "一段纯文本无格式"
    assert case["root_cause"] == ""
    assert case["corrective_action"] == ""
