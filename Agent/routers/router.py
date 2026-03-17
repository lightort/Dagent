from state.agent_state import AgentState


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
        if len(err_msg) > 100:
            err_msg = err_msg[:100] + "..."
        print(f"   ❌ [ERROR]: {err_msg}")

    # 2. 显示决策关键字段
    next_step = state.get("next_step", "")
    print(f"   🎯 [NEXT_STEP]: '{next_step}'")

    # 3. 显示任务类型
    task_type = state.get("task_type", "")
    if task_type:
        print(f"   🧩 [TASK_TYPE]: '{task_type}'")

    # 4. 可选显示 workspace 信息
    summary = state.get("workspace_summary", {})
    if isinstance(summary, dict):
        files_count = len(summary.get("files", []))
        scripts_count = len(summary.get("scripts", []))
        if files_count > 0 or scripts_count > 0:
            print(f"   📂 [WORKSPACE]: {files_count} files, {scripts_count} scripts")

    # 5. 可选显示运行时标志
    if state.get("needs_runtime_inspection") is not None:
        print(f"   🌐 [RUNTIME_NEEDED]: {state.get('needs_runtime_inspection')}")

    # 6. 可选显示浏览器绑定状态
    if state.get("browser_attached") is not None:
        print(f"   🔌 [BROWSER_ATTACHED]: {state.get('browser_attached')}")

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
        "attach_browser_target",
        "runtime_load_page",
        "runtime_capture_dom",
        "runtime_collect_console",
        "runtime_collect_network",
        "search_file",
        "read_file",
        "search_in_file",
        "finish",
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
    valid_routes = {
        "continue",
        "attach_browser_target",
        "runtime_load_page",
        "runtime_capture_dom",
        "runtime_collect_console",
        "runtime_collect_network",
        "done",
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
