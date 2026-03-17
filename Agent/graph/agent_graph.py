from langgraph.graph import StateGraph, END
from state.agent_state import AgentState

from nodes.start_browser import start_browser_node
from nodes.scan_workspace import scan_workspace_node
from nodes.analyze_request import analyze_request_node
from nodes.attach_browser_target import attach_browser_target_node
from nodes.runtime_load_page import runtime_load_page_node
from nodes.runtime_capture_dom import runtime_capture_dom_node
from nodes.runtime_collect_console import runtime_collect_console_node
from nodes.runtime_collect_network import runtime_collect_network_node
from nodes.search_file import search_file_node
from nodes.read_file import read_file_node
from nodes.search_in_file import search_in_file_node
from nodes.check_task_status import check_task_status_node

from routers.router import route_after_analyze, route_after_check


def build_graph():
    builder = StateGraph(AgentState)

    # Register nodes
    builder.add_node("start_browser", start_browser_node)
    builder.add_node("scan_workspace", scan_workspace_node)
    builder.add_node("analyze_request", analyze_request_node)
    builder.add_node("attach_browser_target", attach_browser_target_node)
    builder.add_node("runtime_load_page", runtime_load_page_node)
    builder.add_node("runtime_capture_dom", runtime_capture_dom_node)
    builder.add_node("runtime_collect_console", runtime_collect_console_node)
    builder.add_node("runtime_collect_network", runtime_collect_network_node)
    builder.add_node("search_file", search_file_node)
    builder.add_node("read_file", read_file_node)
    builder.add_node("search_in_file", search_in_file_node)
    builder.add_node("check_task_status", check_task_status_node)

    # Entry point
    builder.set_entry_point("start_browser")

    # Initial flow
    builder.add_conditional_edges(
        "start_browser",
        lambda state: "error" if state.get("error") else "scan_workspace",
        {
            "scan_workspace": "scan_workspace",
            "error": END,
        }
    )
    builder.add_edge("scan_workspace", "analyze_request")

    # analyze_request -> action
    builder.add_conditional_edges(
        "analyze_request",
        route_after_analyze,
        {
            "attach_browser_target": "attach_browser_target",
            "runtime_load_page": "runtime_load_page",
            "runtime_capture_dom": "runtime_capture_dom",
            "runtime_collect_console": "runtime_collect_console",
            "runtime_collect_network": "runtime_collect_network",
            "search_file": "search_file",
            "search_in_file": "search_in_file",
            "read_file": "read_file",
            "finish": END,
            "error": END,
        }
    )

    # attach_browser_target -> back to planner
    builder.add_edge("attach_browser_target", "analyze_request")

    # All action nodes go to check_task_status
    builder.add_edge("runtime_load_page", "check_task_status")
    builder.add_edge("runtime_capture_dom", "check_task_status")
    builder.add_edge("runtime_collect_console", "check_task_status")
    builder.add_edge("runtime_collect_network", "check_task_status")
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
            "runtime_load_page": "runtime_load_page",
            "runtime_capture_dom": "runtime_capture_dom",
            "runtime_collect_console": "runtime_collect_console",
            "runtime_collect_network": "runtime_collect_network",
            "done": END,
            "error": END,
        }
    )

    return builder.compile()
