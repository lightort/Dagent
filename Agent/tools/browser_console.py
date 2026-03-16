from __future__ import annotations

from typing import Any, Dict, List, Optional


def _cdp_call(cdp: Any, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params = params or {}
    #print(f"[CDP_CALL] method={method}, params={params}")

    if hasattr(cdp, "call"):
        #print("[CDP_CALL] using cdp.call(...)")
        result = cdp.call(method, params) or {}
        #print(f"[CDP_CALL] result from call: {result}")
        return result

    if hasattr(cdp, "send"):
        #print("[CDP_CALL] using cdp.send(...)")
        result = cdp.send(method, params) or {}
        #print(f"[CDP_CALL] result from send: {result}")
        return result

    #print("[CDP_CALL] ERROR: cdp client has neither .call nor .send")
    raise AttributeError("CDP client must provide .call(...) or .send(...)")


def _eval(cdp: Any, expression: str, return_by_value: bool = True) -> Any:
    #print("[EVAL] executing Runtime.evaluate")
    #print(f"[EVAL] return_by_value={return_by_value}")
    preview = expression.strip().replace("\n", " ")
    #print(f"[EVAL] expression preview: {preview[:200]}{'...' if len(preview) > 200 else ''}")

    result = _cdp_call(
        cdp,
        "Runtime.evaluate",
        {
            "expression": expression,
            "returnByValue": return_by_value,
            "awaitPromise": True,
        },
    )
    

    #print(f"[EVAL] raw result: {result}")

    if return_by_value:
        value = (((result or {}).get("result") or {}).get("value"))
        #print(f"[EVAL] extracted value: {value}")
        return value

    obj = (result or {}).get("result")
    #print(f"[EVAL] extracted remote object: {obj}")
    return obj


def _enable_console_domains(cdp: Any) -> None:
    #print("[ENABLE] enabling Runtime and Log domains")
    _cdp_call(cdp, "Runtime.enable")
    _cdp_call(cdp, "Log.enable")
    #print("[ENABLE] Runtime and Log enabled")


def install_console_buffer(cdp: Any) -> None:
    """
    在页面里注入一个 console buffer。
    建议在 load_page 后尽快调用，这样后续 console.* 会被记录。
    """
    #print("[INSTALL] install_console_buffer called")
    _enable_console_domains(cdp)

    expression = r"""
    (() => {
        if (window.__RUNTIME_CONSOLE_BUFFER_INSTALLED__) return true;

        window.__RUNTIME_CONSOLE_BUFFER_INSTALLED__ = true;
        window.__RUNTIME_CONSOLE_BUFFER__ = [];

        const levels = ['log', 'info', 'warn', 'error', 'debug'];

        const safeStringify = (args) => {
            return args.map((item) => {
                try {
                    if (typeof item === 'string') return item;
                    return JSON.stringify(item);
                } catch {
                    try { return String(item); } catch { return '[Unserializable]'; }
                }
            }).join(' ');
        };

        for (const level of levels) {
            const original = console[level];
            console[level] = function(...args) {
                try {
                    window.__RUNTIME_CONSOLE_BUFFER__.push({
                        level,
                        message: safeStringify(args),
                        source: 'console',
                        timestamp: new Date().toISOString(),
                    });
                } catch {}
                return original.apply(this, args);
            };
        }

        window.addEventListener('error', function(event) {
            try {
                window.__RUNTIME_CONSOLE_BUFFER__.push({
                    level: 'error',
                    message: event.message || 'Unknown window error',
                    source: 'window.onerror',
                    timestamp: new Date().toISOString(),
                });
            } catch {}
        });

        window.addEventListener('unhandledrejection', function(event) {
            try {
                const reason = event.reason && (event.reason.message || String(event.reason));
                window.__RUNTIME_CONSOLE_BUFFER__.push({
                    level: 'error',
                    message: reason || 'Unhandled promise rejection',
                    source: 'unhandledrejection',
                    timestamp: new Date().toISOString(),
                });
            } catch {}
        });

        return true;
    })()
    """

    result = _eval(cdp, expression, return_by_value=True)
    ##print(f"[INSTALL] console buffer install result: {result}")


def _collect_from_buffer(cdp: Any) -> List[Dict[str, Any]]:
    ##print("[BUFFER] collecting logs from window.__RUNTIME_CONSOLE_BUFFER__")

    expression = r"""
    (() => {
        const data = window.__RUNTIME_CONSOLE_BUFFER__ || [];
        return Array.isArray(data) ? data : [];
    })()
    """
    result = _eval(cdp, expression, return_by_value=True)

    if isinstance(result, list):
        if len(result) > 10:
            ##print(f"[BUFFER] ... and {len(result) - 10} more logs")
            pass
        return result

    ##print(f"[BUFFER] result is not a list: {type(result).__name__}, value={result}")
    return []


def _collect_from_client_events(cdp: Any) -> List[Dict[str, Any]]:
    """
    如果你的 CDP client 有事件缓存能力，可在这里直接取。
    约定:
        cdp.drain_events() -> List[dict]
    """
    ##print("[EVENTS] collecting logs from client events")

    if not hasattr(cdp, "drain_events"):
        ##print("[EVENTS] cdp has no drain_events(), returning []")
        return []

    logs: List[Dict[str, Any]] = []
    events = cdp.drain_events() or []
    ##print(f"[EVENTS] drained {len(events)} raw events")

    for idx, event in enumerate(events, 1):
        method = event.get("method", "")
        params = event.get("params", {}) or {}
        ##print(f"[EVENTS] raw event#{idx}: method={method}, params={params}")

        if method == "Runtime.consoleAPICalled":
            args = params.get("args", []) or []
            texts = []
            for arg in args:
                if "value" in arg:
                    texts.append(str(arg["value"]))
                elif "description" in arg:
                    texts.append(str(arg["description"]))

            log_item = {
                "level": params.get("type", "log"),
                "message": " ".join(texts).strip(),
                "source": "Runtime.consoleAPICalled",
                "timestamp": "",
            }
            logs.append(log_item)
            ##print(f"[EVENTS] parsed consoleAPICalled -> {log_item}")

        elif method == "Log.entryAdded":
            entry = params.get("entry", {}) or {}
            log_item = {
                "level": entry.get("level", "info"),
                "message": entry.get("text", ""),
                "source": entry.get("source", "Log.entryAdded"),
                "timestamp": entry.get("timestamp", ""),
            }
            logs.append(log_item)
            ##print(f"[EVENTS] parsed Log.entryAdded -> {log_item}")

    ##print(f"[EVENTS] collected {len(logs)} console logs from client events")
    return logs


def collect_console_logs(cdp: Any, prefer_client_events: bool = False) -> List[Dict[str, Any]]:
    """
    获取 console 日志。

    默认优先用页面缓冲区，因为它对 client 能力要求更低；
    如果你的 client 能可靠缓存 CDP 事件，可把 prefer_client_events=True。
    """
    ##print("[MAIN] collect_console_logs called")
    ##print(f"[MAIN] prefer_client_events={prefer_client_events}")

    _enable_console_domains(cdp)

    if prefer_client_events:
        ##print("[MAIN] trying client events first")
        logs = _collect_from_client_events(cdp)
        if logs:
            ##print(f"[MAIN] returning {len(logs)} logs from client events")
            return logs
        ###print("[MAIN] no logs from client events, fallback to page buffer")

    ##print("[MAIN] installing console buffer and reading from page")
    install_console_buffer(cdp)
    logs = _collect_from_buffer(cdp)
    ##print(f"[MAIN] returning {len(logs)} logs from page buffer")
    return logs