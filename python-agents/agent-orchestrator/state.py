"""LangGraph 共享状态定义。

编排流程在四个节点（maintenance / quality / scheduler / summary）之间
通过 OrchestratorState 传递中间结果。线性图：每个节点读取上一节点写入
的最新状态，并将自身结果合并写入。

errors 字段采用"读后合并"策略：节点出错时读取当前 errors，追加自身 key
后整体返回，确保多节点连续失败时所有错误都被保留（不依赖 reducer）。
"""

from typing import TypedDict


class OrchestratorState(TypedDict):
    """编排流程共享状态。"""

    # 入参：设备 ID 与故障现象
    device_id: int
    symptom: str

    # 各子 Agent 调用结果（成功为 dict，失败为 None 或 {"status": "skipped", ...}）
    diagnosis: dict | None
    quality_assessment: dict | None
    schedule_adjustment: dict | None

    # 最终 LLM 汇总文本
    summary: str | None

    # 各节点错误信息（key 为节点名，value 为错误描述）
    errors: dict[str, str]
