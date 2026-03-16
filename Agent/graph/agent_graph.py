from langgraph.graph import StateGraph, END

from state.agent_state import AgentState

from nodes.scan_workspace import scan_workspace_node
from nodes.analyze_request import analyze_request_node
from nodes.search_file import search_file_node
from nodes.read_file import read_file_node
from nodes.search_in_file import search_in_file_node
from nodes.modify_code import modify_code_node
from nodes.refactor_code import refactor_code_node
from nodes.apply_patch import apply_patch_node
from nodes.check_task_status import check_task_status_node

from routers.router import route_after_analyze, route_after_check


"""
Graph flow:

scan_workspace
      ↓
analyze_request
      ↓
[route_after_analyze]
   ├── search_file   → check_task_status
   ├── read_file     → check_task_status
   ├── explain_code  → check_task_status
   ├── modify_code   → check_task_status
   ├── refactor_code → check_task_status
   ├── finish        → END
   └── error         → END

check_task_status
   ├── continue    → analyze_request
   ├── apply_patch → apply_patch
   ├── done        → END
   └── error       → END

apply_patch
   ↓
check_task_status
"""


def build_graph():
    builder = StateGraph(AgentState)

    # Register nodes
    builder.add_node("scan_workspace", scan_workspace_node)
    builder.add_node("analyze_request", analyze_request_node)
    builder.add_node("search_file", search_file_node)
    builder.add_node("read_file", read_file_node)
    builder.add_node("search_in_file", search_in_file_node)
    builder.add_node("modify_code", modify_code_node)
    builder.add_node("refactor_code", refactor_code_node)
    builder.add_node("apply_patch", apply_patch_node)
    builder.add_node("check_task_status", check_task_status_node)

    # Entry point
    builder.set_entry_point("scan_workspace")

    # Initial flow
    builder.add_edge("scan_workspace", "analyze_request")

    # analyze_request -> action
    builder.add_conditional_edges(
        "analyze_request",
        route_after_analyze,
        {
            "search_file": "search_file",
            "search_in_file": "search_in_file",
            "read_file": "read_file",
            "modify_code": "modify_code",
            "refactor_code": "refactor_code",
            "finish": END,
            "error": END,
        }
    )

    # All action nodes go to check_task_status
    builder.add_edge("search_file", "check_task_status")
    builder.add_edge("search_in_file", "check_task_status")
    builder.add_edge("read_file", "check_task_status")
    builder.add_edge("modify_code", "check_task_status")
    builder.add_edge("refactor_code", "check_task_status")

    # apply_patch -> check_task_status
    builder.add_edge("apply_patch", "check_task_status")

    # check_task_status -> next step
    builder.add_conditional_edges(
        "check_task_status",
        route_after_check,
        {
            "continue": "analyze_request",
            "apply_patch": "apply_patch",
            "done": END,
            "error": END,
        }
    )

    return builder.compile()