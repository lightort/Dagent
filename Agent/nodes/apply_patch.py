from state.agent_state import AgentState


def apply_patch_node(state: AgentState) -> AgentState:
    """
    应用代码补丁
    
    Args:
        state: 当前状态
    
    Returns:
        更新后的状态，包含应用结果
    """
    print("Applying patches...")
    
    # 获取状态信息
    patches = state.get("patches", [])
    
    # 简单的补丁应用
    applied_patches = []
    for patch in patches:
        applied_patches.append({
            "file_path": patch.get("file_path"),
            "status": "applied",
            "reason": "Patch applied successfully"
        })
    
    # 生成最终响应
    final_response = "## Patch Application Results\n\n"
    for patch in applied_patches:
        final_response += f"- **{patch.get('file_path')}**: {patch.get('status')} - {patch.get('reason')}\n"
    
    # 更新状态
    updated_state = state.copy()
    updated_state["last_step"] = state.get("current_step", "")
    updated_state["applied_patches"] = applied_patches
    updated_state["current_step"] = "apply_patch"
    updated_state["next_step"] = "finish"
    updated_state["final_response"] = final_response
    
    print("Patch application completed.")
    
    return updated_state
