from langgraph.graph import StateGraph, END
from state.agent_state import AgentState
from nodes.variable_analyzer import variable_analyzer_node


def build_variable_analyzer_graph():
    """
    构建变量分析专用图
    
    Returns:
        编译后的StateGraph
    """
    builder = StateGraph(AgentState)

    # 只添加变量分析节点
    builder.add_node("variable_analyzer", variable_analyzer_node)

    # 设置入口点为变量分析节点
    builder.set_entry_point("variable_analyzer")

    # 变量分析完成后结束
    builder.add_edge("variable_analyzer", END)

    return builder.compile()
