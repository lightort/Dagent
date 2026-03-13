from langgraph.graph import StateGraph, END

from state.agent_state import AgentState
from nodes.llm_node import llm_node
from nodes.calculator_node import calculator_node
from routers.router import router


def build_graph():

    builder = StateGraph(AgentState)

    builder.add_node("llm", llm_node)
    builder.add_node("calculator", calculator_node)

    builder.set_entry_point("llm")

    builder.add_conditional_edges(
        "llm",
        router
    )

    builder.add_edge("calculator", END)

    graph = builder.compile()

    return graph