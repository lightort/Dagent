from __future__ import annotations

from typing import Any, Dict, List


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def truncate_text(text: str, max_len: int = 5000) -> str:
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "\n...[TRUNCATED]..."


def summarize_dom(dom: str) -> str:
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


def summarize_console(console_logs: List[Dict[str, Any]]) -> str:
    if not console_logs:
        return "No console logs collected."

    total = len(console_logs)
    error_count = 0
    warn_count = 0

    for log in console_logs:
        level = safe_str(log.get("level", "")).lower()
        if level == "error":
            error_count += 1
        elif level in {"warn", "warning"}:
            warn_count += 1

    return (
        f"Collected {total} console logs. "
        f"errors={error_count}, warnings={warn_count}."
    )


def summarize_network(network_logs: List[Dict[str, Any]]) -> str:
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


def build_runtime_analysis(
    page_meta: Dict[str, Any],
    dom_summary: str,
    console_summary: str,
    network_summary: str,
) -> str:
    title = safe_str(page_meta.get("title", ""))
    url = safe_str(page_meta.get("url", ""))
    ready_state = safe_str(page_meta.get("ready_state", ""))

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
