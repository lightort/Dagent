from __future__ import annotations

from typing import Any, Dict, List

from state.agent_state import AgentState

# 下面这些 import 是基于你当前 tools 命名做的假设。
# 如果你的具体函数名不同，只需要改这里即可。
from tools.browser_page_loader import load_page
from tools.dom_snapshot import capture_dom_snapshot
from tools.browser_console import collect_console_logs
from tools.network_inspector import collect_network_logs


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _truncate_text(text: str, max_len: int = 5000) -> str:
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "\n...[TRUNCATED]..."


def _summarize_dom(dom: str) -> str:
    if not dom:
        return "DOM snapshot is empty."

    summary_parts: List[str] = []
    summary_parts.append(f"DOM captured successfully, length={len(dom)} characters.")

    lowered = dom.lower()
    if "<form" in lowered:
        summary_parts.append("Contains <form> elements.")
    if "<button" in lowered:
        summary_parts.append("Contains <button> elements.")
    if "input" in lowered:
        summary_parts.append("Contains input-related elements.")
    if "modal" in lowered:
        summary_parts.append("Possible modal-related markup detected.")
    if "error" in lowered:
        summary_parts.append("The DOM contains the keyword 'error'.")

    return " ".join(summary_parts)


def _summarize_console(console_logs: List[Dict[str, Any]]) -> str:
    if not console_logs:
        return "No console logs collected."

    total = len(console_logs)
    error_count = 0
    warn_count = 0

    for log in console_logs:
        level = _safe_str(log.get("level", "")).lower()
        if level == "error":
            error_count += 1
        elif level in {"warn", "warning"}:
            warn_count += 1

    return (
        f"Collected {total} console logs. "
        f"errors={error_count}, warnings={warn_count}."
    )


def _summarize_network(network_logs: List[Dict[str, Any]]) -> str:
    if not network_logs:
        return "No network logs collected."

    total = len(network_logs)
    failed_count = 0
    status_4xx_5xx = 0

    for item in network_logs:
        status = item.get("status")
        error = item.get("error")

        if error:
            failed_count += 1

        if isinstance(status, int) and status >= 400:
            status_4xx_5xx += 1

    return (
        f"Collected {total} network records. "
        f"failed={failed_count}, bad_status={status_4xx_5xx}."
    )


def _build_runtime_analysis(
    page_meta: Dict[str, Any],
    dom_summary: str,
    console_summary: str,
    network_summary: str,
) -> str:
    title = _safe_str(page_meta.get("title", ""))
    url = _safe_str(page_meta.get("url", ""))
    ready_state = _safe_str(page_meta.get("ready_state", ""))

    parts = [
        "Runtime inspection completed.",
        f"URL={url or 'N/A'}.",
        f"Title={title or 'N/A'}.",
        f"ReadyState={ready_state or 'N/A'}.",
        dom_summary,
        console_summary,
        network_summary,
    ]
    return " ".join(parts)


def inspect_runtime_node(state: AgentState) -> AgentState:
    """
    运行时检查节点：
    1. 复用现有 CDP 会话加载页面
    2. 抓取 DOM 快照
    3. 收集 console 日志
    4. 收集 network 日志
    5. 写回 AgentState
    """
    new_state: AgentState = dict(state)
    new_state["current_step"] = "inspect_runtime"
    
    print("Inspecting runtime environment...")

    try:
        target_url = _safe_str(new_state.get("target_url", "")).strip()
        if not target_url:
            new_state["error"] = "inspect_runtime requires 'target_url' in state."
            new_state["next_step"] = "error"
            return new_state

        cdp = new_state.get("cdp_session")
        if cdp is None:
            new_state["error"] = "inspect_runtime requires 'cdp_session' in state."
            new_state["next_step"] = "error"
            return new_state
        print(f"Using existing CDP session to inspect runtime for URL: {target_url}")
        print("Step 1: Loading page via CDP...")

        # 1) 页面加载（复用 CDP 会话）
        page_meta = load_page(cdp, target_url=target_url)
        if not isinstance(page_meta, dict):
            page_meta = {}

        print(f"Page loaded. URL: {page_meta.get('url', 'N/A')}, Title: {page_meta.get('title', 'N/A')}, ReadyState: {page_meta.get('ready_state', 'N/A')}")
        print("Step 2: Capturing DOM snapshot...")
        # 2) DOM 快照
        dom = capture_dom_snapshot(cdp)
        dom = _safe_str(dom)
        print(dom[:200] + "..." if len(dom) > 200 else dom)

        print(f"DOM snapshot captured. Length: {len(dom)} characters.")
        print("Step 3: Collecting console logs...")

        # 3) Console
        console_logs = collect_console_logs(cdp)
        if not isinstance(console_logs, list):
            console_logs = []
        
        print(f"Console logs collected. Total logs: {len(console_logs)}.")
        print("Step 4: Collecting network logs...")

        # 4) Network
        network_logs = collect_network_logs(cdp)
        if not isinstance(network_logs, list):
            network_logs = []
        
        print(f"Network logs collected. Total records: {len(network_logs)}.")
        # 5) 摘要
        dom_summary = _summarize_dom(dom)
        console_summary = _summarize_console(console_logs)
        network_summary = _summarize_network(network_logs)
        runtime_analysis = _build_runtime_analysis(
            page_meta=page_meta,
            dom_summary=dom_summary,
            console_summary=console_summary,
            network_summary=network_summary,
        )

        # 6) 写回 state
        new_state["runtime_page_meta"] = {
            "url": _safe_str(page_meta.get("url", target_url)),
            "title": _safe_str(page_meta.get("title", "")),
            "ready_state": _safe_str(page_meta.get("ready_state", "")),
            "html_length": len(dom),
        }
        new_state["runtime_dom"] = _truncate_text(dom, max_len=20000)
        new_state["runtime_dom_summary"] = dom_summary
        new_state["console_logs"] = console_logs
        new_state["console_summary"] = console_summary
        new_state["network_logs"] = network_logs
        new_state["network_summary"] = network_summary
        new_state["runtime_analysis"] = runtime_analysis

        # runtime 做完后，不在这里强行决定复杂流转；
        # 统一交给 check_task_status_node 去判断更稳。
        new_state["error"] = None
        new_state["next_step"] = "continue"

        # 可选：把 analysis 补强一下，方便后续 analyze_request 使用
        previous_analysis = _safe_str(new_state.get("analysis", ""))
        merged_analysis = (
            runtime_analysis
            if not previous_analysis
            else previous_analysis + "\n\n[Runtime Inspection]\n" + runtime_analysis
        )
        new_state["analysis"] = merged_analysis

        return new_state

    except Exception as e:
        new_state["error"] = f"inspect_runtime failed: {e}"
        new_state["next_step"] = "error"
        return new_state