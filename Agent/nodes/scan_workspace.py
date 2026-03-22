from state.agent_state import AgentState
import os
from tools.workspace_scanner import workspace_scanner



import os
import re
from urllib.parse import unquote, urlparse

import os
import re
from urllib.parse import unquote, urlparse

def _parse_scanner_output(output: str) -> list[str]:
    """
    解析 scanner 输出，提取纯净的本地文件路径列表。
    自动过滤日志，处理 file:// URL，并修复 Windows 路径格式。
    """
    if not output:
        return []

    if output.startswith("[error]") or output.startswith("[stderr]"):
        return []

    result = []
    # 匹配 file:// 开头的 URL
    url_pattern = re.compile(r'(file://[^\s]+)')

    for line in output.split("\n"):
        line = line.strip()
        if not line:
            continue

        match = url_pattern.search(line)
        if match:
            file_url = match.group(1)
            try:
                parsed = urlparse(file_url)
                # 解码 URL 编码 (如 %20 -> 空格)
                local_path = unquote(parsed.path)
                
                # 【核心修复】针对 Windows 路径的特殊处理
                if os.name == 'nt':
                    # 情况 1: 路径以 /C:/ 或 /D:/ 开头 (常见于 file:///C:/...)
                    # 我们需要去掉开头的 '/'
                    if len(local_path) > 2 and local_path[0] == '/' and local_path[2] == ':':
                        local_path = local_path[1:]
                    
                    # 情况 2: 极端情况下可能还有多个斜杠，循环去除直到符合盘符格式
                    while len(local_path) > 2 and local_path[0] == '/' and local_path[2] == ':':
                        local_path = local_path[1:]
                        
                    # 可选：将正斜杠 / 替换为反斜杠 \ (Windows 原生风格，虽非必须但更规范)
                    # local_path = local_path.replace('/', '\\')

                # 再次确认路径是否存在
                if os.path.exists(local_path):
                    result.append(local_path)
                else:
                    # 如果依然不存在，可能是权限问题或路径真的错了，这里选择静默跳过
                    # 如需调试，可取消下面这行的注释
                    # print(f"[WARN] 路径不存在: {local_path}")
                    pass

            except Exception:
                # 解析失败跳过
                continue

    return result

def scan_workspace_node(state: AgentState) -> AgentState:
    """
    扫描工作区目录，生成工作区摘要
    """
    print("Scanning workspace...")

    updated_state = state.copy()
    workspace_root = state.get("workspace_root") or os.getcwd()

    updated_state["current_step"] = "scan_workspace"
    updated_state["workspace_root"] = workspace_root
    updated_state["browser_attached"] = False  
    updated_state["target_url"] = "file:///C:/Users/14590/Desktop/Dagent/WebPage/index.html"
    workspace_summary = {
        "root": workspace_root,
        "directories": [],
        "files": [],
        "scripts": [],
        "structure": {},
    }

    try:
        flat_output = workspace_scanner(workspace_root, mode="flat")
        print("Workspace scanner output:", flat_output)

        if flat_output.startswith("[error]"):
            updated_state["error"] = flat_output
            updated_state["workspace_summary"] = workspace_summary
            return updated_state

        scripts_output = workspace_scanner(workspace_root, mode="scripts")
        print("Scripts scanner output:", scripts_output)


        workspace_summary["files"] = _parse_scanner_output(flat_output)
        workspace_summary["scripts"] = _parse_scanner_output(scripts_output)
    

        updated_state["workspace_summary"] = workspace_summary
        updated_state["error"] = None

        print(f"Workspace scanned. Found {len(workspace_summary['files'])} files.")

    except Exception as e:
        updated_state["error"] = f"Error scanning workspace: {e}"
        updated_state["workspace_summary"] = workspace_summary
        print(updated_state["error"])

    return updated_state