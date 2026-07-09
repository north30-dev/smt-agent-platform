"""LangGraph 编译图。

线性编排：START → maintenance → quality → scheduler → summary → END
线性图保证每个节点都执行，不会因某节点失败而短路，
配合 nodes 层的 AgentUnavailable 降级策略实现"部分失败仍跑完"。
"""

from langgraph.graph import END, START, StateGraph

from .nodes import (
    maintenance_node,
    quality_node,
    scheduler_node,
    summary_node,
)
from .state import OrchestratorState


def build_graph():
    """构建并编译 LangGraph 编排图。

    Returns:
        编译后的 CompiledStateGraph，支持 ainvoke / invoke。
    """
    g = StateGraph(OrchestratorState)
    g.add_node("maintenance", maintenance_node)
    g.add_node("quality", quality_node)
    g.add_node("scheduler", scheduler_node)
    g.add_node("summary", summary_node)
    g.add_edge(START, "maintenance")
    g.add_edge("maintenance", "quality")
    g.add_edge("quality", "scheduler")
    g.add_edge("scheduler", "summary")
    g.add_edge("summary", END)
    return g.compile()


# 模块级编译图单例
app_graph = build_graph()
