"""agent_maintenance.diagnose 单元测试。

使用 monkeypatch 替换 diagnose 模块内已 import 的 shared 引用
（llm_client / vector_store）与 device_client，不依赖真实 Milvus、
大模型与 Java device-service。

P0 B1：diagnose.create_case/diagnose 已改 async，测试同步改 async def + AsyncMock。
- llm_client.embed/chat → AsyncMock（被 await 调用）
- device_client.get_device → AsyncMock（被 await 调用）
- vector_store.insert/init_collections/search → MagicMock（被 asyncio.to_thread 包装为同步）
"""

from unittest.mock import AsyncMock, MagicMock

from agent_maintenance.diagnose import COLLECTION, create_case, diagnose


async def test_create_case(monkeypatch):
    """录入案例应串联 embed → init_collections → insert，并返回非空 case_id。"""
    # 重置懒初始化标志，保证本用例触发 init_collections
    monkeypatch.setattr("agent_maintenance.diagnose._initialized", False)

    mock_llm = MagicMock()
    mock_llm.embed = AsyncMock(return_value=[[0.1, 0.2]])
    monkeypatch.setattr("agent_maintenance.diagnose.llm_client", mock_llm)

    mock_vs = MagicMock()
    mock_vs.insert.return_value = 1
    mock_vs.count.return_value = 1
    monkeypatch.setattr("agent_maintenance.diagnose.vector_store", mock_vs)

    case_id = await create_case("MOUNTER", "异响", "轴承磨损", "更换轴承")

    assert case_id.startswith("case-")
    assert len(case_id) == len("case-") + 8
    mock_llm.embed.assert_called_once()
    mock_vs.init_collections.assert_called_once_with(2)
    mock_vs.insert.assert_called_once()
    # insert 入参：collection, doc_id, chunks, vectors
    args = mock_vs.insert.call_args.args
    assert args[0] == COLLECTION
    assert args[1] == case_id
    assert len(args[2]) == 1
    assert "MOUNTER" in args[2][0]


async def test_diagnose_success(monkeypatch):
    """诊断应串联 get_device → embed → search → chat，并解析 LLM 输出。"""
    mock_device = MagicMock()
    mock_device.get_device = AsyncMock(return_value={"id": 1, "deviceName": "贴片机"})
    monkeypatch.setattr("agent_maintenance.diagnose.device_client", mock_device)

    mock_llm = MagicMock()
    mock_llm.embed = AsyncMock(return_value=[[0.1, 0.2]])
    mock_llm.chat = AsyncMock(
        return_value='{"root_causes": ["轴承磨损"], "repair_suggestions": ["更换轴承"]}'
    )
    monkeypatch.setattr("agent_maintenance.diagnose.llm_client", mock_llm)

    mock_vs = MagicMock()
    mock_vs.search.return_value = [
        {
            "doc_id": "c1",
            "chunk_id": 0,
            "content": "设备类型：MOUNTER\n症状：异响\n根因：轴承磨损\n解决方案：更换",
            "score": 0.9,
        }
    ]
    monkeypatch.setattr("agent_maintenance.diagnose.vector_store", mock_vs)

    result = await diagnose(1, "异响")

    assert result["root_causes"] == ["轴承磨损"]
    assert result["repair_suggestions"] == ["更换轴承"]
    assert len(result["similar_cases"]) == 1
    case = result["similar_cases"][0]
    assert case["case_id"] == "c1"
    assert case["score"] == 0.9
    assert case["symptom"] == "异响"
    assert case["root_cause"] == "轴承磨损"
    assert case["solution"] == "更换"

    mock_device.get_device.assert_called_once_with(1)
    mock_llm.embed.assert_called_once_with(["异响"])
    mock_vs.search.assert_called_once()
    mock_llm.chat.assert_called_once()
    # chat 收到 system + user 两条消息
    messages = mock_llm.chat.call_args.args[0]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    # user 消息应包含故障现象与 JSON 输出要求
    assert "异响" in messages[1]["content"]
    assert "root_causes" in messages[1]["content"]


async def test_diagnose_llm_not_json(monkeypatch):
    """LLM 输出非 JSON 时应降级为 root_causes=[raw_text]、repair_suggestions=[]。"""
    mock_device = MagicMock()
    mock_device.get_device = AsyncMock(return_value={"id": 1, "deviceName": "贴片机"})
    monkeypatch.setattr("agent_maintenance.diagnose.device_client", mock_device)

    mock_llm = MagicMock()
    mock_llm.embed = AsyncMock(return_value=[[0.1, 0.2]])
    mock_llm.chat = AsyncMock(return_value="无法解析")
    monkeypatch.setattr("agent_maintenance.diagnose.llm_client", mock_llm)

    mock_vs = MagicMock()
    mock_vs.search.return_value = []
    monkeypatch.setattr("agent_maintenance.diagnose.vector_store", mock_vs)

    result = await diagnose(1, "异响")

    assert result["root_causes"] == ["无法解析"]
    assert result["repair_suggestions"] == []
    assert result["similar_cases"] == []
