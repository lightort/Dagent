from state.agent_state import AgentState


def route_after_analyze(state: AgentState) -> str:
    print("STATE IN ROUTER:", state)

    if state.get("error"):
        print("ROUTING TO ERROR")
        return "error"

    task_type = state.get("task_type")

    if task_type in {"explain", "debug", "modify", "refactor"}:
        print("ROUTING TO SEARCH")
        return task_type

    print("ROUTING TO FINISH")
    return "finish"

from state.agent_state import AgentState


def route_after_search(state: AgentState) -> str:
    print("STATE IN ROUTER:", state)

    if state.get("error"):
        print("ROUTING TO ERROR")
        return "error"

    if not state.get("selected_files"):
        print("NO FILES FOUND, ROUTING TO FINISH")
        return "finish"

    task_type = state.get("task_type")

    if task_type == "explain":
        print("ROUTING TO EXPLAIN")
        return "explain"
    elif task_type == "debug":
        print("ROUTING TO DEBUG")
        return "debug"
    elif task_type == "modify":
        print("ROUTING TO MODIFY")
        return "modify"
    elif task_type == "refactor":
        print("ROUTING TO REFACTOR")
        return "refactor"

    print("UNKNOWN TASK, ROUTING TO FINISH")
    return "finish"