from __future__ import annotations

from state.agent_state import AgentState
from tools.browser_console import collect_console_logs
from tools.runtime_helpers import summarize_console


def runtime_collect_console_node(state: AgentState) -> AgentState:
    new_state: AgentState = dict(state)
    new_state["current_step"] = "runtime_collect_console"
    new_state["last_step"] = state.get("current_step", "")
    new_state["error"] = None

    try:
        cdp = new_state.get("cdp_session")
        if cdp is None:
            new_state["error"] = "runtime_collect_console requires 'cdp_session' in state."
            new_state["next_step"] = "error"
            return new_state

        console_logs = collect_console_logs(cdp)
        if not isinstance(console_logs, list):
            console_logs = []

        new_state["console_logs"] = console_logs
        new_state["console_summary"] = summarize_console(console_logs)
        return new_state

    except Exception as e:
        new_state["error"] = f"runtime_collect_console failed: {e}"
        new_state["next_step"] = "error"
        return new_state
