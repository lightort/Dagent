from langgraph.graph import StateGraph, END
from state.agent_state import AgentState

from nodes.scan_workspace import scan_workspace_node
from nodes.analyze_request import analyze_request_node
from nodes.attach_browser_target import attach_browser_target_node
from nodes.inspect_runtime import inspect_runtime_node
from nodes.search_file import search_file_node
from nodes.read_file import read_file_node
from nodes.search_in_file import search_in_file_node
from nodes.check_task_status import check_task_status_node

from routers.router import route_after_analyze, route_after_check


def build_graph():
    builder = StateGraph(AgentState)

    # Register nodes
    builder.add_node("scan_workspace", scan_workspace_node)
    builder.add_node("analyze_request", analyze_request_node)
    builder.add_node("attach_browser_target", attach_browser_target_node)
    builder.add_node("inspect_runtime", inspect_runtime_node)
    builder.add_node("search_file", search_file_node)
    builder.add_node("read_file", read_file_node)
    builder.add_node("search_in_file", search_in_file_node)
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
            "attach_browser_target": "attach_browser_target",
            "inspect_runtime": "inspect_runtime",
            "search_file": "search_file",
            "search_in_file": "search_in_file",
            "read_file": "read_file",
            "finish": END,
            "error": END,
        }
    )

    # attach_browser_target -> inspect_runtime
    builder.add_edge("attach_browser_target", "inspect_runtime")

    # All action nodes go to check_task_status
    builder.add_edge("inspect_runtime", "check_task_status")
    builder.add_edge("search_file", "check_task_status")
    builder.add_edge("search_in_file", "check_task_status")
    builder.add_edge("read_file", "check_task_status")


    # check_task_status -> next step
    builder.add_conditional_edges(
        "check_task_status",
        route_after_check,
        {
            "continue": "analyze_request",
            "attach_browser_target": "attach_browser_target",
            "inspect_runtime": "inspect_runtime",
            "done": END,
            "error": END,
        }
    )

    return builder.compile()