from state.agent_state import AgentState
import os
from tools.file_reader import file_reader


def explain_code_node(state: AgentState) -> AgentState:
    """
    解释代码或返回目录结构
    
    Args:
        state: 当前状态
    
    Returns:
        更新后的状态，包含最终响应
    """
    print("Explaining code or directory structure...")
    
    # 获取用户请求和工作区摘要
    user_request = state.get("user_request", "").lower()
    workspace_summary = state.get("workspace_summary", {})
    selected_files = state.get("selected_files", [])
    workspace_root = state.get("workspace_root", os.getcwd())
    
    # 生成响应
    final_response = ""
    
    # 处理查看目录请求
    if any(keyword in user_request for keyword in ["目录", "结构", "list", "dir", "ls"]):
        final_response = "## 工作区目录结构\n\n"
        
        # 添加根目录信息
        final_response += f"**根目录**: {workspace_root}\n\n"
        
        # 添加文件列表
        files = workspace_summary.get("files", [])
        if files:
            final_response += "### 文件列表\n"
            for file in files:
                final_response += f"- {file}\n"
    
    # 处理查看文件内容请求
    elif any(keyword in user_request for keyword in ["查看", "内容", "文件", "read", "view"]):
        if selected_files:
            final_response = "## 文件内容\n\n"
            for file_path in selected_files:
                # 使用file_reader工具读取文件内容
                content = file_reader(file_path)
                
                if "[error]" in content:
                    final_response += f"### {file_path}\n**错误**: {content}\n\n"
                else:
                    final_response += f"### {file_path}\n\n```\n{content}\n```\n\n"
        else:
            final_response = "## 错误\n\n未找到要查看的文件，请在请求中明确指定文件名。"
    
    # 处理其他请求
    else:
        final_response = "## 信息\n\n请明确您的请求，例如：\n- 查看目录结构\n- 查看文件内容 (请指定文件名)"
    
    # 更新状态
    updated_state = state.copy()
    updated_state["final_response"] = final_response
    updated_state["current_step"] = "explain_code"
    updated_state["next_step"] = "finish"
    
    print("Explanation completed.")
    
    return updated_state
