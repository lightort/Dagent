import subprocess
import time

from state.agent_state import AgentState
from tools.browser_console import install_console_buffer
from tools.cdp_target_resolver import resolve_cdp_target
from tools.network_inspector import install_network_buffer


def start_browser_node(state: AgentState) -> AgentState:
    """
    Start Chrome with remote debugging enabled and open the target page.
    """
    updated_state = state.copy()
    updated_state["current_step"] = "start_browser"
    updated_state["last_step"] = state.get("current_step", "")
    updated_state["error"] = None
    remote_debugging_url = str(
        state.get("remote_debugging_url", "http://127.0.0.1:9222")
    ).strip()
    target_url = str(
        state.get(
            "target_url",
            "file:///C:/Users/14590/Desktop/Dagent/WebPage/index.html",
        )
    ).strip()
    updated_state["remote_debugging_url"] = remote_debugging_url
    updated_state["target_url"] = target_url
    updated_state["browser_attached"] = False
    updated_state["operation_history"] = state.get("operation_history", []) + ["start_browser"]

    ps_script = fr"""
Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue
Start-Process -FilePath "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  -ArgumentList "--remote-debugging-port=9222", "--remote-allow-origins=*", "--user-data-dir=C:\tmp\chrome-cdp-profile", "{target_url}"
"""

    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            check=True,
            capture_output=True,
            text=True,
        )

        # Inject console listener as early as possible, so later collection includes prior logs.
        last_error = None
        for _ in range(20):
            try:
                result = resolve_cdp_target(
                    remote_debugging_url=remote_debugging_url,
                    target_url=target_url,
                    timeout=3.0,
                )
                cdp = result.get("cdp_session")
                if cdp is None:
                    raise RuntimeError("cdp_session is None after resolve_cdp_target")

                install_console_buffer(cdp)
                install_network_buffer(cdp)
                if hasattr(cdp, "close"):
                    cdp.close()

                updated_state["console_listener_installed"] = True
                updated_state["network_listener_installed"] = True
                last_error = None
                break
            except Exception as e:
                last_error = e
                time.sleep(0.5)

        if last_error is not None:
            raise RuntimeError(f"Failed to inject console listener: {last_error}")
    except Exception as e:
        updated_state["error"] = f"Failed to start Chrome: {e}"

    return updated_state
