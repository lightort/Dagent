from __future__ import annotations

from typing import Any, Dict, Optional


def _cdp_call(cdp: Any, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params = params or {}
    if hasattr(cdp, "call"):
        return cdp.call(method, params) or {}
    if hasattr(cdp, "send"):
        return cdp.send(method, params) or {}
    raise AttributeError("CDP client must provide .call(...) or .send(...)")


def _eval_return_value(cdp: Any, expression: str) -> str:
    result = _cdp_call(
        cdp,
        "Runtime.evaluate",
        {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
        },
    )
    value = (((result or {}).get("result") or {}).get("value"))
    return "" if value is None else str(value)


def capture_dom_snapshot(
    cdp: Any,
    selector: Optional[str] = None,
    mode: str = "outerHTML",
) -> str:
    """
    抓取运行时 DOM。

    参数:
        cdp: 已连接的 CDP client
        selector: 可选；如果为空则抓全页 document.documentElement.outerHTML
        mode: outerHTML / innerText / textContent

    返回:
        str
    """
    _cdp_call(cdp, "DOM.enable")
    _cdp_call(cdp, "Runtime.enable")

    if selector is None or not str(selector).strip():
        return _eval_return_value(cdp, "document.documentElement?.outerHTML || ''")

    selector_escaped = selector.replace("\\", "\\\\").replace("'", "\\'")
    if mode == "innerText":
        expression = f"""
        (() => {{
            const el = document.querySelector('{selector_escaped}');
            return el ? (el.innerText || '') : '';
        }})()
        """
    elif mode == "textContent":
        expression = f"""
        (() => {{
            const el = document.querySelector('{selector_escaped}');
            return el ? (el.textContent || '') : '';
        }})()
        """
    else:
        expression = f"""
        (() => {{
            const el = document.querySelector('{selector_escaped}');
            return el ? (el.outerHTML || '') : '';
        }})()
        """

    return _eval_return_value(cdp, expression)


def capture_dom_metadata(cdp: Any) -> Dict[str, Any]:
    print("[DOM_META] start")

    _cdp_call(cdp, "DOM.enable")
    print("[DOM_META] DOM.enable done")

    _cdp_call(cdp, "Runtime.enable")
    print("[DOM_META] Runtime.enable done")

    title = _eval_return_value(cdp, "document.title || ''")
    print(f"[DOM_META] title={title}")

    ready_state = _eval_return_value(cdp, "document.readyState || ''")
    print(f"[DOM_META] ready_state={ready_state}")

    body_text_length = _eval_return_value(cdp, "(document.body && document.body.innerText || '').length")
    print(f"[DOM_META] body_text_length={body_text_length}")

    forms_count = _eval_return_value(cdp, "document.querySelectorAll('form').length")
    print(f"[DOM_META] forms_count={forms_count}")

    buttons_count = _eval_return_value(cdp, "document.querySelectorAll('button').length")
    print(f"[DOM_META] buttons_count={buttons_count}")

    links_count = _eval_return_value(cdp, "document.querySelectorAll('a').length")
    print(f"[DOM_META] links_count={links_count}")

    print(
        f"Captured DOM metadata. "
        f"Title: {title}, ReadyState: {ready_state}, BodyTextLength: {body_text_length}, "
        f"FormsCount: {forms_count}, ButtonsCount: {buttons_count}, LinksCount: {links_count}"
    )

    return {
        "title": title,
        "ready_state": ready_state,
        "body_text_length": int(body_text_length or 0),
        "forms_count": int(forms_count or 0),
        "buttons_count": int(buttons_count or 0),
        "links_count": int(links_count or 0),
    }