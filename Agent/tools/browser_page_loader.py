from __future__ import annotations

import os
import re
import time
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urlparse


def _cdp_call(cdp: Any, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params = params or {}
    if hasattr(cdp, "call"):
        return cdp.call(method, params) or {}
    if hasattr(cdp, "send"):
        return cdp.send(method, params) or {}
    raise AttributeError("CDP client must provide .call(...) or .send(...)")


def _safe_eval(cdp: Any, expression: str) -> Any:
    result = _cdp_call(
        cdp,
        "Runtime.evaluate",
        {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
        },
    )
    return (((result or {}).get("result") or {}).get("value"))


def _enable_domains(cdp: Any) -> None:
    _cdp_call(cdp, "Page.enable")
    _cdp_call(cdp, "Runtime.enable")
    _cdp_call(cdp, "DOM.enable")
    # Network 在 network_inspector 中也会启，这里不强依赖


def _wait_for_ready_state(
    cdp: Any,
    timeout: float = 10.0,
    poll_interval: float = 0.2,
    expected_states: tuple[str, ...] = ("interactive", "complete"),
) -> str:
    deadline = time.time() + timeout
    last_state = ""

    while time.time() < deadline:
        state = _safe_eval(cdp, "document.readyState") or ""
        last_state = str(state)
        if last_state in expected_states:
            return last_state
        time.sleep(poll_interval)

    return last_state


def _safe_filename_from_url(url: str) -> str:
    parsed = urlparse(url or "")
    candidate = parsed.path.strip("/") if parsed.path else ""
    candidate = candidate.split("/")[-1] if candidate else "page"
    if not candidate.lower().endswith(".html"):
        candidate = f"{candidate}.html"
    candidate = re.sub(r"[^a-zA-Z0-9._-]", "_", candidate)
    if not candidate or candidate == ".html":
        candidate = "page.html"
    return candidate


def _save_html_snapshot(html: str, current_url: str, output_dir: str = "htmls") -> str:
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = _safe_filename_from_url(current_url)
    file_path = os.path.join(output_dir, f"{timestamp}_{filename}")
    with open(file_path, "w", encoding="utf-8", errors="replace") as f:
        f.write(html or "")
    return os.path.abspath(file_path)


def load_page(
    cdp: Any,
    target_url: Optional[str] = None,
    timeout: float = 15.0,
    wait_until_ready: bool = True,
    save_html: bool = True,
    html_output_dir: str = r"C:\Users\14590\Desktop\Dagent\Agent\download\htmls",
) -> Dict[str, Any]:
    """
    加载页面并返回页面基础信息。

    参数:
        cdp: 已连接的 CDP client
        target_url: 可选；如果传入则执行 Page.navigate
        timeout: 等待页面 ready 的超时时间
        wait_until_ready: 是否等待 document.readyState

    返回:
        {
            "url": str,
            "title": str,
            "ready_state": str,
            "html_length": int,
            "navigation_performed": bool
        }
    """
    _enable_domains(cdp)

    navigation_performed = False
    if target_url:
        _cdp_call(cdp, "Page.navigate", {"url": target_url})
        navigation_performed = True

    ready_state = ""
    if wait_until_ready:
        ready_state = _wait_for_ready_state(cdp, timeout=timeout)

    current_url = _safe_eval(cdp, "window.location.href") or (target_url or "")
    title = _safe_eval(cdp, "document.title") or ""
    html = _safe_eval(cdp, "document.documentElement?.outerHTML || ''") or ""
    saved_html_path = ""
    if save_html:
        try:
            saved_html_path = _save_html_snapshot(
                html=str(html),
                current_url=str(current_url),
                output_dir=html_output_dir,
            )
            print(f"[LOAD_PAGE] HTML snapshot saved to: {saved_html_path}")
        except Exception as e:
            print(f"[LOAD_PAGE] Failed to save HTML snapshot: {e}")

    print(f"[LOAD_PAGE] URL={current_url}, Title={title}, ReadyState={ready_state}, HTML length={len(html)}, Navigation performed={navigation_performed}")

    return {
        "url": str(current_url),
        "title": str(title),
        "ready_state": str(ready_state),
        "html_length": len(str(html)),
        "navigation_performed": navigation_performed,
        "saved_html_path": saved_html_path,
    }
