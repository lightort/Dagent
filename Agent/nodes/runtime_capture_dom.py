from __future__ import annotations

from state.agent_state import AgentState
from tools.dom_snapshot import capture_dom_snapshot
from tools.runtime_helpers import safe_str, summarize_dom, truncate_text


def runtime_capture_dom_node(state: AgentState) -> AgentState:
    new_state: AgentState = dict(state)
    new_state["current_step"] = "runtime_capture_dom"
    new_state["last_step"] = state.get("current_step", "")
    new_state["error"] = None
    new_state["operation_history"] = state.get("operation_history", []) + ["runtime_capture_dom"]
    try:
        cdp = new_state.get("cdp_session")
        if cdp is None:
            new_state["error"] = "runtime_capture_dom requires 'cdp_session' in state."
            new_state["next_step"] = "error"
            return new_state

        dom = safe_str(capture_dom_snapshot(cdp))
        dom_summary = summarize_dom(dom)

        page_meta = dict(new_state.get("runtime_page_meta", {}) or {})
        page_meta["html_length"] = len(dom)

        new_state["runtime_page_meta"] = page_meta
        new_state["runtime_dom"] = truncate_text(dom, max_len=20000)
        new_state["runtime_dom_summary"] = dom_summary
        return new_state

    except Exception as e:
        new_state["error"] = f"runtime_capture_dom failed: {e}"
        new_state["next_step"] = "error"
        return new_state
