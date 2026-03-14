from state.agent_state import AgentState
import os
from tools.workspace_scanner import workspace_scanner
from typing import Dict, Any


def scan_workspace_node(state: AgentState) -> AgentState:
    """
    扫描工作区目录，生成工作区摘要
    
    Args:
        state: 当前状态
    
    Returns:
        更新后的状态，包含工作区摘要
    """
    print("Scanning workspace...")
    
    # 获取工作区根目录
    workspace_root = state.get("workspace_root", os.getcwd())
    
    # 扫描目录结构
    workspace_summary = {
        "root": workspace_root,
        "directories": [],
        "files": [],
        "structure": {}
    }
    
    # 使用workspace_scanner工具获取目录结构
    try:
        # 获取所有文件
        flat_output = workspace_scanner(mode="flat")
        print("Workspace scanner output:", flat_output)
        
        # 解析输出
        lines = flat_output.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('['):
                workspace_summary["files"].append(line)
        
        # 获取scripts文件
        scripts_output = workspace_scanner(mode="scripts")
        print("Scripts scanner output:", scripts_output)
        
    except Exception as e:
        print(f"Error scanning workspace: {e}")
    
    # 更新状态
    updated_state = state.copy()
    updated_state["workspace_root"] = workspace_root
    updated_state["workspace_summary"] = workspace_summary
    updated_state["current_step"] = "scan_workspace"
    updated_state["next_step"] = "analyze_request"
    
    print(f"Workspace scanned. Found {len(workspace_summary['files'])} files.")
    
    return updated_state
