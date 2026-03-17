from __future__ import annotations

from state.agent_state import AgentState
from tools.browser_page_loader import load_page
from tools.runtime_helpers import safe_str


def runtime_load_page_node(state: AgentState) -> AgentState:
    new_state: AgentState = dict(state)
    new_state["current_step"] = "runtime_load_page"
    new_state["last_step"] = state.get("current_step", "")
    new_state["error"] = None

    try:
        target_url = safe_str(new_state.get("target_url", "")).strip()
        if not target_url:
            new_state["error"] = "runtime_load_page requires 'target_url' in state."
            new_state["next_step"] = "error"
            return new_state

        cdp = new_state.get("cdp_session")
        if cdp is None:
            new_state["error"] = "runtime_load_page requires 'cdp_session' in state."
            new_state["next_step"] = "error"
            return new_state

        page_meta = load_page(cdp, target_url=target_url)
        if not isinstance(page_meta, dict):
            page_meta = {}

        new_state["runtime_page_meta"] = {
            "url": safe_str(page_meta.get("url", target_url)),
            "title": safe_str(page_meta.get("title", "")),
            "ready_state": safe_str(page_meta.get("ready_state", "")),
            "html_length": int(new_state.get("runtime_page_meta", {}).get("html_length", 0) or 0),
            "saved_html_path": safe_str(page_meta.get("saved_html_path", "")),
        }
        return new_state

    except Exception as e:
        new_state["error"] = f"runtime_load_page failed: {e}"
        new_state["next_step"] = "error"
        return new_state
