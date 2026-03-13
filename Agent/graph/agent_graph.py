from langgraph.graph import StateGraph, END

from state.agent_state import AgentState

from nodes.scan_workspace import scan_workspace_node
from nodes.analyze_request import analyze_request_node
from nodes.search_code import search_code_node
from nodes.explain_code import explain_code_node
from nodes.find_bug import find_bug_node
from nodes.modify_code import modify_code_node
from nodes.refactor_code import refactor_code_node
from nodes.apply_patch import apply_patch_node

from routers.router import route_after_analyze


'''
scan_workspace
      ↓
analyze_request
      ↓
   [route_after_analyze]
   ├── explain  → search_code → [route_after_analyze] → explain_code  → END
   ├── debug    → search_code → [route_after_analyze] → find_bug      → END
   ├── modify   → search_code → [route_after_analyze] → modify_code   → apply_patch → END
   ├── refactor → search_code → [route_after_analyze] → refactor_code → apply_patch → END
   ├── finish   → END
   └── error    → END
'''

def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("scan_workspace", scan_workspace_node)
    builder.add_node("analyze_request", analyze_request_node)
    builder.add_node("search_code", search_code_node)
    builder.add_node("explain_code", explain_code_node)
    builder.add_node("find_bug", find_bug_node)
    builder.add_node("modify_code", modify_code_node)
    builder.add_node("refactor_code", refactor_code_node)
    builder.add_node("apply_patch", apply_patch_node)

    builder.set_entry_point("scan_workspace")

    builder.add_edge("scan_workspace", "analyze_request")

    builder.add_conditional_edges(
        "analyze_request",
        route_after_analyze,
        {
            "explain": "search_code",
            "debug": "search_code",
            "modify": "search_code",
            "refactor": "search_code",
            "finish": END,
            "error": END,
        }
    )

    builder.add_conditional_edges(
        "search_code",
        route_after_analyze,
        {
            "explain": "explain_code",
            "debug": "find_bug",
            "modify": "modify_code",
            "refactor": "refactor_code",
            "finish": END,
            "error": END,
        }
    )

    builder.add_edge("explain_code", END)
    builder.add_edge("find_bug", END)
    builder.add_edge("modify_code", "apply_patch")
    builder.add_edge("refactor_code", "apply_patch")
    builder.add_edge("apply_patch", END)

    return builder.compile()