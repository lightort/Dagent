from __future__ import annotations

from state.agent_state import AgentState
from tools.cdp_target_resolver import resolve_cdp_target


def _safe_str(value, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def attach_browser_target_node(state: AgentState) -> AgentState:
    """
    绑定浏览器目标页面节点：
    1. 从 state 中读取 remote_debugging_url 和 target_url
    2. 解析 Chrome 当前 target 列表
    3. 找到与 target_url 对应的页面
    4. 建立 cdp_session
    5. 将结果写回 state
    """
    new_state: AgentState = dict(state)
    new_state["current_step"] = "attach_browser_target"
    new_state["last_step"] = state.get("current_step", "")

    try:
        remote_debugging_url = _safe_str(
            new_state.get("remote_debugging_url", "http://127.0.0.1:9222")
        ).strip()
        target_url = _safe_str(new_state.get("target_url", "")).strip()
        print(f"Attaching browser target. Remote Debugging URL: {remote_debugging_url}, Target URL: {target_url}")
        if not target_url:
            new_state["error"] = "attach_browser_target requires 'target_url' in state."
            new_state["browser_attached"] = False
            new_state["next_step"] = "error"
            return new_state

        result = resolve_cdp_target(
            remote_debugging_url=remote_debugging_url,
            target_url=target_url,
        )

        cdp_session = result.get("cdp_session")
        target_info = result.get("target_info", {}) or {}

        if cdp_session is None:
            new_state["error"] = f"Failed to attach browser target for url: {target_url}"
            new_state["browser_attached"] = False
            new_state["next_step"] = "error"
            return new_state

        new_state["remote_debugging_url"] = remote_debugging_url
        new_state["cdp_session"] = cdp_session
        new_state["cdp_target_info"] = {
            "id": _safe_str(target_info.get("id", "")),
            "title": _safe_str(target_info.get("title", "")),
            "url": _safe_str(target_info.get("url", target_url)),
            "type": _safe_str(target_info.get("type", "page")),
            "webSocketDebuggerUrl": _safe_str(target_info.get("webSocketDebuggerUrl", "")),
        }
        new_state["browser_attached"] = True
        new_state["error"] = None

        # 绑定成功后直接进入运行时检查
        new_state["next_step"] = "error" if not new_state["browser_attached"] else "inspect_runtime"
        return new_state

    except Exception as e:
        new_state["error"] = f"attach_browser_target failed: {e}"
        new_state["browser_attached"] = False
        new_state["next_step"] = "error"
        return new_state