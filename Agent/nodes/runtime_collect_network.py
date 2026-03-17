from __future__ import annotations

from state.agent_state import AgentState
from tools.network_inspector import collect_network_logs
from tools.runtime_helpers import (
    build_runtime_analysis,
    safe_str,
    summarize_network,
)


def runtime_collect_network_node(state: AgentState) -> AgentState:
    new_state: AgentState = dict(state)
    new_state["current_step"] = "runtime_collect_network"
    new_state["last_step"] = state.get("current_step", "")
    new_state["error"] = None
    new_state["operation_history"] = state.get("operation_history", []) + ["runtime_collect_network"]

    try:
        cdp = new_state.get("cdp_session")
        if cdp is None:
            new_state["error"] = "runtime_collect_network requires 'cdp_session' in state."
            new_state["next_step"] = "error"
            return new_state

        network_logs = collect_network_logs(cdp)
        if not isinstance(network_logs, list):
            network_logs = []

        network_summary = summarize_network(network_logs)
        page_meta = dict(new_state.get("runtime_page_meta", {}) or {})
        dom_summary = safe_str(new_state.get("runtime_dom_summary", ""))
        console_summary = safe_str(new_state.get("console_summary", ""))

        runtime_analysis = build_runtime_analysis(
            page_meta=page_meta,
            dom_summary=dom_summary,
            console_summary=console_summary,
            network_summary=network_summary,
        )

        previous_analysis = safe_str(new_state.get("analysis", ""))
        merged_analysis = (
            runtime_analysis
            if not previous_analysis
            else previous_analysis + "\n\n[Runtime Inspection]\n" + runtime_analysis
        )

        new_state["network_logs"] = network_logs
        new_state["network_summary"] = network_summary
        new_state["runtime_analysis"] = runtime_analysis
        new_state["analysis"] = merged_analysis
        new_state["next_step"] = "continue"
        return new_state

    except Exception as e:
        new_state["error"] = f"runtime_collect_network failed: {e}"
        new_state["next_step"] = "error"
        return new_state
