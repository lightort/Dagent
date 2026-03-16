from state.agent_state import AgentState
import json

def _print_separator(title: str):
    """打印一个带有标题的分隔线，使日志区块分明"""
    print("\n" + "=" * 60)
    print(f"🚀 {title}")
    print("=" * 60)

def _print_state_summary(state: AgentState, context: str):
    """
    精简打印 State 的关键信息，避免刷屏。
    """
    print(f"📍 [{context}] 当前状态摘要:")
    
    # 1. 错误优先显示
    if state.get("error"):
        err_msg = str(state["error"])
        # 截断过长的错误信息
        if len(err_msg) > 100:
            err_msg = err_msg[:100] + "..."
        print(f"   ❌ [ERROR]: {err_msg}")
    
    # 2. 显示决策关键字段
    next_step = state.get("next_step", "")
    print(f"   🎯 [NEXT_STEP]: '{next_step}'")
    
    # 3. 可选：显示 workspace_summary 的文件数量（如果存在）
    summary = state.get("workspace_summary", {})
    if isinstance(summary, dict):
        files_count = len(summary.get("files", []))
        scripts_count = len(summary.get("scripts", []))
        if files_count > 0 or scripts_count > 0:
            print(f"   📂 [WORKSPACE]: {files_count} files, {scripts_count} scripts")
            
    print("-" * 40)

def route_after_analyze(state: AgentState) -> str:
    _print_separator("路由决策: 分析后 (After Analyze)")
    _print_state_summary(state, "Analyze")

    # 1. 检查错误
    if state.get("error"):
        print("⛔ 决策结果: 检测到错误 -> 转向 [error]")
        return "error"

    next_step = state.get("next_step", "").strip()
    valid_routes = {
        "search_file", "read_file", "search_in_file",
        "find_bug", "modify_code", "refactor_code", "finish"
    }

    # 2. 验证路由
    if next_step in valid_routes:
        print(f"✅ 决策结果: 有效步骤 -> 转向 [{next_step.upper()}]")
        print("=" * 60 + "\n")
        return next_step

    # 3. 处理无效路由
    print(f"⚠️ 决策结果: 无效步骤 '{next_step}' -> 强制转向 [error]")
    print("=" * 60 + "\n")
    return "error"


def route_after_check(state: AgentState) -> str:
    _print_separator("路由决策: 检查后 (After Check)")
    _print_state_summary(state, "Check")

    # 1. 检查错误
    if state.get("error"):
        print("⛔ 决策结果: 检测到错误 -> 转向 [error]")
        return "error"

    next_step = state.get("next_step", "").strip()
    valid_routes = {"continue", "apply_patch", "done"}

    # 2. 验证路由
    if next_step in valid_routes:
        print(f"✅ 决策结果: 有效步骤 -> 转向 [{next_step.upper()}]")
        print("=" * 60 + "\n")
        return next_step

    # 3. 处理无效路由
    print(f"⚠️ 决策结果: 无效步骤 '{next_step}' -> 强制转向 [error]")
    print("=" * 60 + "\n")
    return "error"