from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


def _cdp_call(cdp: Any, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params = params or {}
    if hasattr(cdp, "call"):
        return cdp.call(method, params) or {}
    if hasattr(cdp, "send"):
        return cdp.send(method, params) or {}
    raise AttributeError("CDP client must provide .call(...) or .send(...)")


def _eval(cdp: Any, expression: str, return_by_value: bool = True):
    result = _cdp_call(
        cdp,
        "Runtime.evaluate",
        {
            "expression": expression,
            "returnByValue": return_by_value,
            "awaitPromise": True,
        },
    )
    if return_by_value:
        return (((result or {}).get("result") or {}).get("value"))
    return (result or {}).get("result")


def _enable_network_domains(cdp: Any) -> None:
    _cdp_call(cdp, "Runtime.enable")
    _cdp_call(cdp, "Network.enable")


def install_network_buffer(cdp: Any) -> None:
    """
    在页面中注入 fetch / XHR 监控缓冲区。
    """
    _enable_network_domains(cdp)

    expression = r"""
    (() => {
        if (window.__RUNTIME_NETWORK_BUFFER_INSTALLED__) return true;

        window.__RUNTIME_NETWORK_BUFFER_INSTALLED__ = true;
        window.__RUNTIME_NETWORK_BUFFER__ = [];

        const pushRecord = (record) => {
            try {
                window.__RUNTIME_NETWORK_BUFFER__.push({
                    url: record.url || '',
                    method: record.method || 'GET',
                    status: Number(record.status || 0),
                    resource_type: record.resource_type || 'unknown',
                    error: record.error || '',
                    timestamp: new Date().toISOString(),
                });
            } catch {}
        };

        // Hook fetch
        if (window.fetch) {
            const originalFetch = window.fetch;
            window.fetch = async function(...args) {
                const input = args[0];
                const init = args[1] || {};
                const url = typeof input === 'string' ? input : (input?.url || '');
                const method = init.method || 'GET';

                try {
                    const response = await originalFetch.apply(this, args);
                    pushRecord({
                        url,
                        method,
                        status: response.status,
                        resource_type: 'fetch',
                        error: '',
                    });
                    return response;
                } catch (err) {
                    pushRecord({
                        url,
                        method,
                        status: 0,
                        resource_type: 'fetch',
                        error: err?.message || String(err),
                    });
                    throw err;
                }
            };
        }

        // Hook XHR
        if (window.XMLHttpRequest) {
            const OriginalXHR = window.XMLHttpRequest;

            function PatchedXHR() {
                const xhr = new OriginalXHR();
                let method = 'GET';
                let url = '';

                const originalOpen = xhr.open;
                xhr.open = function(m, u, ...rest) {
                    method = m || 'GET';
                    url = u || '';
                    return originalOpen.call(this, m, u, ...rest);
                };

                xhr.addEventListener('loadend', function() {
                    pushRecord({
                        url,
                        method,
                        status: xhr.status || 0,
                        resource_type: 'xhr',
                        error: '',
                    });
                });

                xhr.addEventListener('error', function() {
                    pushRecord({
                        url,
                        method,
                        status: xhr.status || 0,
                        resource_type: 'xhr',
                        error: 'XHR network error',
                    });
                });

                return xhr;
            }

            window.XMLHttpRequest = PatchedXHR;
        }

        return true;
    })()
    """
    _eval(cdp, expression, return_by_value=True)


def _collect_from_buffer(cdp: Any) -> List[Dict[str, Any]]:
    expression = r"""
    (() => {
        const data = window.__RUNTIME_NETWORK_BUFFER__ || [];
        return Array.isArray(data) ? data : [];
    })()
    """
    result = _eval(cdp, expression, return_by_value=True)
    return result if isinstance(result, list) else []


def _collect_from_client_events(cdp: Any) -> List[Dict[str, Any]]:
    """
    如果你的 client 有事件缓存能力，可直接解析 Network.* 事件。
    """
    if not hasattr(cdp, "drain_events"):
        return []

    events = cdp.drain_events() or []
    request_map: Dict[str, Dict[str, Any]] = {}
    logs: List[Dict[str, Any]] = []

    for event in events:
        method = event.get("method", "")
        params = event.get("params", {}) or {}

        if method == "Network.requestWillBeSent":
            request_id = params.get("requestId", "")
            request = params.get("request", {}) or {}
            request_map[request_id] = {
                "url": request.get("url", ""),
                "method": request.get("method", "GET"),
                "status": 0,
                "resource_type": params.get("type", "unknown"),
                "error": "",
            }

        elif method == "Network.responseReceived":
            request_id = params.get("requestId", "")
            response = params.get("response", {}) or {}
            if request_id in request_map:
                request_map[request_id]["status"] = int(response.get("status", 0))

        elif method == "Network.loadingFailed":
            request_id = params.get("requestId", "")
            error_text = params.get("errorText", "")
            base = request_map.get(
                request_id,
                {
                    "url": "",
                    "method": "GET",
                    "status": 0,
                    "resource_type": "unknown",
                    "error": "",
                },
            )
            base["error"] = error_text or "loadingFailed"
            logs.append(base)

        elif method == "Network.loadingFinished":
            request_id = params.get("requestId", "")
            if request_id in request_map:
                logs.append(request_map[request_id])

    return logs


def _save_network_logs(
    logs: List[Dict[str, Any]],
    output_dir: str = r"C:\Users\14590\Desktop\Dagent\Agent\download\networks",
) -> str:
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(output_dir, f"{timestamp}_network_logs.json")
    with open(file_path, "w", encoding="utf-8", errors="replace") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)
    return os.path.abspath(file_path)


def collect_network_logs(
    cdp: Any,
    prefer_client_events: bool = False,
    save_to_file: bool = True,
) -> List[Dict[str, Any]]:
    """
    获取网络请求日志。
    默认优先用页面缓冲区。
    """
    _enable_network_domains(cdp)

    if prefer_client_events:
        logs = _collect_from_client_events(cdp)
        if logs:
            if save_to_file:
                try:
                    saved_path = _save_network_logs(logs)
                    print(f"[NETWORK] logs saved to: {saved_path}")
                except Exception as e:
                    print(f"[NETWORK] save failed: {e}")
            return logs

    install_network_buffer(cdp)
    logs = _collect_from_buffer(cdp)
    if save_to_file:
        try:
            saved_path = _save_network_logs(logs)
            print(f"[NETWORK] logs saved to: {saved_path}")
        except Exception as e:
            print(f"[NETWORK] save failed: {e}")
    return logs
