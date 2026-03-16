from __future__ import annotations

import json
import urllib.request
import urllib.parse
from typing import Any, Dict, List, Optional

from websocket import create_connection


class CDPSession:
    """
    一个最小可用的 CDP WebSocket 会话封装。
    提供:
      - call(method, params)
      - send(method, params)  # call 的别名
      - close()
    """

    def __init__(self, websocket_url: str, timeout: float = 10.0):
        self.websocket_url = websocket_url
        self.timeout = timeout
        self._ws = create_connection(websocket_url, timeout=timeout)
        self._message_id = 0

    def call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._message_id += 1
        payload = {
            "id": self._message_id,
            "method": method,
            "params": params or {},
        }

        self._ws.send(json.dumps(payload))

        while True:
            raw = self._ws.recv()
            message = json.loads(raw)

            # 忽略事件消息，只等当前 id 的响应
            if "id" not in message:
                continue

            if message["id"] != self._message_id:
                continue

            if "error" in message:
                raise RuntimeError(
                    f"CDP call failed: method={method}, error={message['error']}"
                )

            return message.get("result", {}) or {}

    def send(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.call(method, params)

    def close(self) -> None:
        try:
            self._ws.close()
        except Exception:
            pass


def _normalize_debugging_url(remote_debugging_url: str) -> str:
    value = (remote_debugging_url or "").strip().rstrip("/")
    if not value:
        return "http://127.0.0.1:9222"
    return value


def _fetch_targets(remote_debugging_url: str) -> List[Dict[str, Any]]:
    """
    从 Chrome DevTools 调试端口读取 target 列表。
    优先使用 /json/list，失败时回退到 /json。
    """
    base = _normalize_debugging_url(remote_debugging_url)
    candidate_urls = [
        f"{base}/json/list",
        f"{base}/json",
    ]

    last_error: Optional[Exception] = None

    for url in candidate_urls:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                data = response.read().decode("utf-8")
                parsed = json.loads(data)
                if isinstance(parsed, list):
                    return parsed
        except Exception as e:
            last_error = e

    raise RuntimeError(f"Failed to fetch Chrome targets from {base}: {last_error}")


def _normalize_target_url(target_url: str) -> str:
    """
    统一 target_url 形式。
    这里只做最轻量规范化，不强行改动 file:/// 结构。
    """
    value = (target_url or "").strip()
    return value


def _score_target_match(target: Dict[str, Any], target_url: str) -> int:
    """
    给 target 和目标 URL 做一个简单匹配打分。
    分数越高越优先。
    """
    url = str(target.get("url", "")).strip()
    title = str(target.get("title", "")).strip()
    target_type = str(target.get("type", "")).strip()

    if target_type != "page":
        return -1

    if not url:
        return 0

    if url == target_url:
        return 100

    # 宽松匹配：忽略末尾斜杠
    if url.rstrip("/") == target_url.rstrip("/"):
        return 90

    # file URL 常见情况：title 可能是 index.html
    if target_url.endswith(title) and title:
        return 50

    # 包含关系，兜底
    if target_url in url or url in target_url:
        return 30

    return 0


def _find_best_target(targets: List[Dict[str, Any]], target_url: str) -> Dict[str, Any]:
    normalized_target_url = _normalize_target_url(target_url)

    scored_targets = []
    for target in targets:
        score = _score_target_match(target, normalized_target_url)
        if score > 0:
            scored_targets.append((score, target))

    if not scored_targets:
        available = [
            {
                "type": t.get("type", ""),
                "title": t.get("title", ""),
                "url": t.get("url", ""),
            }
            for t in targets
        ]
        raise RuntimeError(
            f"No matching Chrome target found for target_url={normalized_target_url}. "
            f"Available targets={available}"
        )

    scored_targets.sort(key=lambda item: item[0], reverse=True)
    return scored_targets[0][1]


def _connect_target(target: Dict[str, Any], timeout: float = 10.0) -> CDPSession:
    websocket_url = str(target.get("webSocketDebuggerUrl", "")).strip()
    if not websocket_url:
        raise RuntimeError(f"Target does not contain webSocketDebuggerUrl: {target}")

    return CDPSession(websocket_url=websocket_url, timeout=timeout)


def resolve_cdp_target(
    remote_debugging_url: str,
    target_url: str,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """
    根据 remote_debugging_url + target_url:
      1. 获取 Chrome 当前全部 target
      2. 找到匹配的页面 target
      3. 建立 WebSocket CDP 会话
      4. 返回 cdp_session 与 target_info

    返回:
    {
        "cdp_session": CDPSession(...),
        "target_info": {
            "id": "...",
            "title": "...",
            "url": "...",
            "type": "page",
            "webSocketDebuggerUrl": "ws://..."
        }
    }
    """
    normalized_debug_url = _normalize_debugging_url(remote_debugging_url)
    normalized_target_url = _normalize_target_url(target_url)

    if not normalized_target_url:
        raise ValueError("target_url is required")

    targets = _fetch_targets(normalized_debug_url)
    best_target = _find_best_target(targets, normalized_target_url)
    session = _connect_target(best_target, timeout=timeout)

    target_info = {
        "id": str(best_target.get("id", "")),
        "title": str(best_target.get("title", "")),
        "url": str(best_target.get("url", "")),
        "type": str(best_target.get("type", "")),
        "webSocketDebuggerUrl": str(best_target.get("webSocketDebuggerUrl", "")),
    }
    print(f"Resolved CDP target. Target URL: {target_info['url']}, Title: {target_info['title']}")

    return {
        "cdp_session": session,
        "target_info": target_info,
    }