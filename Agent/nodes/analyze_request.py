import json
from state.agent_state import AgentState
from config.model_config import llm


SYSTEM_PROMPT = """
你是网页代码分析 Agent 的决策节点。
你的职责是根据当前 AgentState 选择下一步要执行的节点。

只允许输出 JSON，不要输出任何额外文本。

task_type 只能是：
- search
- attach browser

next_step 只能是：
- attach_browser_target
- runtime_load_page
- runtime_capture_dom
- runtime_collect_console
- runtime_collect_network
- search_file
- search_in_file
- read_file
- finish

当前图逻辑（关键）：
1. 入口先完成浏览器启动和 workspace 扫描。
2. analyze_request 决定动作节点。
3. attach_browser_target 执行后会回到 analyze_request。
4. runtime_* / search_file / search_in_file / read_file 执行后会进入 check_task_status。
5. 仅当任务已经可结束时才选择 finish。

决策约束：
1. 如果需要运行时信息且 browser_attached=False，优先 attach_browser_target。
2. 如果需要运行时信息且 browser_attached=True，可在 runtime_* 四个节点中按需选择任意一个。
3. search_phase=file 时优先 search_file。
4. search_phase=chunk 时优先 search_in_file。
5. search_phase=read 时优先 read_file。
6. search_phase=action 时再考虑 runtime_* / attach_browser_target / finish / search_file。
7. analysis 要简洁说明选择依据。

输出格式：
{
  "task_type": "...",
  "analysis": "...",
  "next_step": "..."
}
"""


def _safe_json_load(text: str) -> dict:
    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]

    return json.loads(text)


def analyze_request_node(state: AgentState) -> AgentState:
    """
    使用 LLM 分析当前请求和上下文，结合 search_phase 决定下一步动作
    """
    print("Analyzing user request by LLM...")

    updated_state = state.copy()
    updated_state["current_step"] = "analyze_request"
    updated_state["error"] = None

    try:
        updated_state["last_step"] = state.get("current_step", "")
        user_request = state.get("user_request", "")
        workspace_summary = state.get("workspace_summary", {})
        candidate_files = state.get("candidate_files", [])
        selected_files = state.get("selected_files", [])
        code_context = state.get("code_context", [])
        analysis = state.get("analysis", "")
        plan = state.get("plan", [])
        task_type = state.get("task_type", "")
        search_phase = state.get("search_phase", "").strip()
        remote_debugging_url = state.get("remote_debugging_url", "")
        target_url = state.get("target_url", "")
        browser_attached = state.get("browser_attached", False)
        runtime_page_meta = state.get("runtime_page_meta", {})
        runtime_dom_summary = state.get("runtime_dom_summary", "")
        console_summary = state.get("console_summary", "")
        network_summary = state.get("network_summary", "")
        runtime_analysis = state.get("runtime_analysis", "")
        needs_runtime_inspection = state.get("needs_runtime_inspection", False)

        has_candidate_files = bool(candidate_files)
        has_selected_files = bool(selected_files)
        has_code_context = bool(code_context)

        user_prompt = f"""
当前 AgentState 关键信息如下：

user_request:
{user_request}

task_type:
{task_type}

search_phase:
{search_phase}

needs_runtime_inspection:
{needs_runtime_inspection}

browser_attached:
{browser_attached}

remote_debugging_url:
{remote_debugging_url}

target_url:
{target_url}

workspace_summary:
{json.dumps(workspace_summary, ensure_ascii=False)}

candidate_files:
{json.dumps(candidate_files, ensure_ascii=False)}

selected_files:
{json.dumps(selected_files, ensure_ascii=False)}

code_context:
{json.dumps(code_context, ensure_ascii=False)}

runtime_page_meta:
{json.dumps(runtime_page_meta, ensure_ascii=False)}

runtime_dom_summary:
{runtime_dom_summary}

console_summary:
{console_summary}

network_summary:
{network_summary}

runtime_analysis:
{runtime_analysis}

analysis:
{analysis}

plan:
{json.dumps(plan, ensure_ascii=False)}

状态辅助：
has_candidate_files: {has_candidate_files}
has_selected_files: {has_selected_files}
has_code_context: {has_code_context}
has_runtime_analysis: {bool(runtime_analysis)}

请输出：
1. task_type
2. analysis
3. next_step

仅输出 JSON。
"""
        response = llm.invoke([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ])

        content = response.content if hasattr(response, "content") else str(response)
        print("LLM raw response:", content)

        result = _safe_json_load(content)

        new_task_type = result.get("task_type", "").strip()
        new_analysis = result.get("analysis", "").strip()
        next_step = result.get("next_step", "").strip()

        valid_task_types = {"search", "attach browser"}
        valid_next_steps = {
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

        if new_task_type not in valid_task_types:
            raise ValueError(f"Invalid task_type from LLM: {new_task_type}")

        if next_step not in valid_next_steps:
            raise ValueError(f"Invalid next_step from LLM: {next_step}")

        # # -------------------------
        # # 鍩轰簬 search_phase 鐨勭‖绾︽潫绾犲亸
        # # -------------------------

        # if search_phase == "file":
        #     if next_step != "search_file":
        #         print(f"Correcting next_step from {next_step} to search_file because search_phase=file.")
        #         next_step = "search_file"

        # elif search_phase == "chunk":
        #     if not selected_files:
        #         print("Correcting next_step to search_file because search_phase=chunk but selected_files is empty.")
        #         next_step = "search_file"
        #     elif next_step != "search_in_file":
        #         print(f"Correcting next_step from {next_step} to search_in_file because search_phase=chunk.")
        #         next_step = "search_in_file"

        # elif search_phase == "read":
        #     if not code_context:
        #         if selected_files:
        #             print("Correcting next_step to search_in_file because search_phase=read but code_context is empty.")
        #             next_step = "search_in_file"
        #         else:
        #             print("Correcting next_step to search_file because search_phase=read but selected_files is empty.")
        #             next_step = "search_file"
        #     elif next_step != "read_file":
        #         print(f"Correcting next_step from {next_step} to read_file because search_phase=read.")
        #         next_step = "read_file"

        # elif search_phase == "action":
        #     # action 闃舵鍏堢湅 runtime 闇€姹?
        #     if needs_runtime_inspection:
        #         if not browser_attached:
        #             if next_step != "attach_browser_target":
        #                 print(f"Correcting next_step from {next_step} to attach_browser_target because runtime is needed and browser is not attached.")
        #                 next_step = "attach_browser_target"
        #         elif not runtime_analysis:
        #             if next_step != "runtime_load_page":
        #                 print(f"Correcting next_step from {next_step} to runtime_load_page because runtime is needed and runtime analysis is missing.")
        #                 next_step = "runtime_load_page"
        #         else:
        #             # 宸叉湁 runtime 淇℃伅锛屽啀鑰冭檻鍔ㄤ綔
        #             if new_task_type == "modify":
        #                 if next_step not in {"modify_code", "search_file", "finish"}:
        #                     print(f"Correcting next_step from {next_step} to modify_code in action phase.")
        #                     next_step = "modify_code"
        #             elif new_task_type == "refactor":
        #                 if next_step not in {"refactor_code", "search_file", "finish"}:
        #                     print(f"Correcting next_step from {next_step} to refactor_code in action phase.")
        #                     next_step = "refactor_code"
        #             elif new_task_type == "debug":
        #                 if next_step not in {"search_file", "runtime_load_page", "finish"}:
        #                     print(f"Correcting next_step from {next_step} to search_file for debug task in action phase.")
        #                     next_step = "search_file"
        #             else:
        #                 if next_step not in {"search_file", "finish"}:
        #                     print(f"Correcting next_step from {next_step} to search_file for search task in action phase.")
        #                     next_step = "search_file"
        #     else:
        #         # 涓嶉渶瑕?runtime锛屾寜闈欐€佸垎鏋愭祦璧?
        #         if not code_context:
        #             if selected_files:
        #                 print("Correcting next_step to search_in_file because search_phase=action but code_context is empty.")
        #                 next_step = "search_in_file"
        #             else:
        #                 print("Correcting next_step to search_file because search_phase=action but selected_files is empty.")
        #                 next_step = "search_file"
        #         else:
        #             if new_task_type == "modify":
        #                 if next_step not in {"modify_code", "search_file", "finish"}:
        #                     print(f"Correcting next_step from {next_step} to modify_code in static action phase.")
        #                     next_step = "modify_code"
        #             elif new_task_type == "refactor":
        #                 if next_step not in {"refactor_code", "search_file", "finish"}:
        #                     print(f"Correcting next_step from {next_step} to refactor_code in static action phase.")
        #                     next_step = "refactor_code"
        #             elif new_task_type in {"debug", "search"}:
        #                 if next_step not in {"search_file", "finish"}:
        #                     print(f"Correcting next_step from {next_step} to search_file in static action phase.")
        #                     next_step = "search_file"

        # elif search_phase == "done":
        #     if next_step != "finish":
        #         print(f"Correcting next_step from {next_step} to finish because search_phase=done.")
        #         next_step = "finish"

        # else:
        #     print(f"Unknown search_phase: {search_phase}, applying fallback correction.")
        #     if needs_runtime_inspection and not browser_attached:
        #         next_step = "attach_browser_target"
        #     elif needs_runtime_inspection and browser_attached and not runtime_analysis:
        #         next_step = "runtime_load_page"
        #     elif not selected_files:
        #         next_step = "search_file"
        #     elif not code_context:
        #         next_step = "search_in_file"
        #     else:
        #         if new_task_type == "modify":
        #             next_step = "modify_code"
        #         elif new_task_type == "refactor":
        #             next_step = "refactor_code"
        #         elif new_task_type in {"debug", "search"}:
        #             next_step = "search_file"
        #         else:
        #             next_step = "finish"

        updated_state["task_type"] = new_task_type
        updated_state["analysis"] = new_analysis
        updated_state["next_step"] = next_step

        print(
            f"Request analyzed. "
            f"task_type={new_task_type}, search_phase={search_phase}, next_step={next_step}"
        )
        return updated_state

    except Exception as e:
        updated_state["error"] = f"Error analyzing request: {e}"
        updated_state["next_step"] = "error"
        print(updated_state["error"])
        return updated_state


