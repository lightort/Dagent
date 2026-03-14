from state.agent_state import AgentState
import re


def analyze_request_node(state: AgentState) -> AgentState:
    """
    分析用户请求，确定任务类型
    
    Args:
        state: 当前状态
    
    Returns:
        更新后的状态，包含任务类型
    """
    print("Analyzing user request...")
    
    # 获取用户请求
    user_request = state.get("user_request", "").lower()
    
    # 暂时只将需求变为explain
    task_type = "explain"
    analysis = "用户请求查看或解释内容"
    
    # 更新状态
    updated_state = state.copy()
    updated_state["task_type"] = task_type
    updated_state["analysis"] = analysis
    updated_state["current_step"] = "analyze_request"
    
    # 确定下一步
    if task_type in {"explain", "debug", "modify", "refactor", "search"}:
        updated_state["next_step"] = task_type
    else:
        updated_state["next_step"] = "finish"
    
    print(f"Request analyzed. Task type: {task_type}")
    
    return updated_state
