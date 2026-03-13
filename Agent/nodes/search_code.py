from state.agent_state import AgentState
import os


def search_code_node(state: AgentState) -> AgentState:
    """
    搜索相关代码文件
    
    Args:
        state: 当前状态
    
    Returns:
        更新后的状态，包含候选文件列表
    """
    print("Searching for relevant code...")
    
    # 获取用户请求和工作区摘要
    user_request = state.get("user_request", "").lower()
    workspace_summary = state.get("workspace_summary", {})
    files = workspace_summary.get("files", [])
    
    # 搜索相关文件
    candidate_files = []
    
    # 对于查看目录请求，不需要搜索文件
    if any(keyword in user_request for keyword in ["目录", "结构", "list", "dir", "ls"]):
        candidate_files = []
    
    # 对于查看文件内容请求，提取文件名
    elif any(keyword in user_request for keyword in ["查看", "内容", "文件", "read", "view"]):
        # 简单的文件名提取
        words = user_request.split()
        for word in words:
            if any(word.endswith(ext) for ext in ['.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css']):
                # 查找匹配的文件
                for file_path in files:
                    if word in file_path:
                        candidate_files.append(file_path)
                        break
    
    # 其他请求，搜索相关文件
    else:
        # 简单的关键词匹配
        for file_path in files:
            if any(keyword in file_path for keyword in user_request.split()):
                candidate_files.append(file_path)
    
    # 限制候选文件数量
    candidate_files = candidate_files[:10]  # 最多返回10个文件
    
    # 更新状态
    updated_state = state.copy()
    updated_state["candidate_files"] = candidate_files
    updated_state["selected_files"] = candidate_files  # 直接选择所有候选文件
    updated_state["current_step"] = "search_code"
    
    # 确定下一步
    task_type = state.get("task_type")
    if task_type in {"explain", "debug", "modify", "refactor"}:
        updated_state["next_step"] = task_type
    else:
        updated_state["next_step"] = "finish"
    
    print(f"Search completed. Found {len(candidate_files)} relevant files.")
    
    return updated_state
