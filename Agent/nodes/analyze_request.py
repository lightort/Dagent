import json
from state.agent_state import AgentState
from config.model_config import llm


SYSTEM_PROMPT = """
你是一个网页代码分析 Agent 的决策中枢。
你的任务不是直接修改代码，而是根据当前状态决定“下一步应该进入哪个节点”。

你必须只输出 JSON，不能输出任何额外解释、markdown、代码块。

你可选择的 task_type 只有：
- debug
- modify
- refactor
- search

你可选择的 next_step 只有：
- attach_browser_target  绑定浏览器目标页面
- inspect_runtime        获取运行时页面信息（DOM / console / network）
- search_file            寻找相关文件
- search_in_file         在相关文件中定位相关代码片段
- read_file              基于已经定位到的代码片段扩展上下文并精读
- modify_code            修改代码
- refactor_code          重构代码
- finish                 任务完成

节点职责定义：
1. attach_browser_target 负责绑定正确的浏览器 target，并建立 cdp_session ，之后可以续接 inspect_runtime 采集运行时信息
2. inspect_runtime 只负责基于已有 cdp_session 采集运行时信息
3. search_file 只负责找“文件”
4. search_in_file 只负责在 selected_files 中找“相关代码片段”，并产出 code_context
5. read_file 只负责基于已有 code_context 扩展上下文并精读
6. modify_code / refactor_code 只在已经有足够上下文时使用
7. search_file 既可以用于初始找文件，也可以用于 action 阶段切换到新的文件继续探索

search_phase 含义：
- file   = 还在文件级定位阶段
- chunk  = 已经找到文件，正在文件内定位片段
- read   = 已经定位到片段，准备精读
- action = 已经有足够上下文，可以执行具体任务或继续探索
- done   = 任务已完成

决策原则：
1. task_type 表示任务语义；next_step 表示下一步节点，两者不要混淆
2. 如果任务需要运行时信息，优先判断是否已完成浏览器绑定
3. 如果需要运行时信息且 browser_attached 为 false，应选择 attach_browser_target
4. 如果需要运行时信息且 browser_attached 为 true，但尚缺 runtime 信息，应选择 inspect_runtime
5. 如果 search_phase 是 file，通常应选择 search_file
6. 如果 search_phase 是 chunk，通常应选择 search_in_file
7. 如果 search_phase 是 read，通常应选择 read_file
8. 如果 search_phase 是 action，才应考虑 attach_browser_target / inspect_runtime / modify_code / refactor_code / finish / search_file
9. 只有在任务已经足够完成时，才能选择 finish
10. analysis 要简洁说明判断依据

输出格式必须严格为：
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
        user_request = state.get("user_request", "")
        workspace_summary = state.get("workspace_summary", {})
        candidate_files = state.get("candidate_files", [])
        selected_files = state.get("selected_files", [])
        code_context = state.get("code_context", [])
        analysis = state.get("analysis", "")
        plan = state.get("plan", [])
        patches = state.get("patches", [])
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
        has_patches = bool(patches)

        user_prompt = f"""
当前 AgentState 关键信息如下：

user_request:
{user_request}

已有 task_type:
{task_type}

search_phase:
{search_phase}

needs_runtime_inspection:
{needs_runtime_inspection}

remote_debugging_url:
{remote_debugging_url}

target_url:
{target_url}

browser_attached:
{browser_attached}

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

patches:
{json.dumps(patches, ensure_ascii=False)}

状态判断辅助字段：
has_candidate_files: {has_candidate_files}
has_selected_files: {has_selected_files}
has_code_context: {has_code_context}
has_patches: {has_patches}
has_runtime_analysis: {bool(runtime_analysis)}

请基于以上状态，判断：
1. 当前任务类型 task_type
2. 当前分析结论 analysis
3. 下一步 next_step

注意：
- 优先遵守 search_phase 所代表的阶段语义
- 如果需要运行时信息且 browser_attached=False，应优先选择 attach_browser_target
- 如果需要运行时信息且 browser_attached=True，但还缺少运行时结果，应优先选择 inspect_runtime
- 如果 search_phase=file，不要跳过 search_file
- 如果 search_phase=chunk，不要跳过 search_in_file
- 如果 search_phase=read，不要跳过 read_file
- 如果 search_phase=action，才考虑 attach_browser_target / inspect_runtime / modify_code / refactor_code / finish / search_file
- 只能输出 JSON
- next_step 只能是 attach_browser_target / inspect_runtime / search_file / read_file / search_in_file / modify_code / refactor_code / finish
- task_type 只能是 debug / modify / refactor / search
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

        valid_task_types = {"debug", "modify", "refactor", "search"}
        valid_next_steps = {
            "attach_browser_target",
            "inspect_runtime",
            "search_file",
            "read_file",
            "search_in_file",
            "modify_code",
            "refactor_code",
            "finish",
        }

        if new_task_type not in valid_task_types:
            raise ValueError(f"Invalid task_type from LLM: {new_task_type}")

        if next_step not in valid_next_steps:
            raise ValueError(f"Invalid next_step from LLM: {next_step}")

        # # -------------------------
        # # 基于 search_phase 的硬约束纠偏
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
        #     # action 阶段先看 runtime 需求
        #     if needs_runtime_inspection:
        #         if not browser_attached:
        #             if next_step != "attach_browser_target":
        #                 print(f"Correcting next_step from {next_step} to attach_browser_target because runtime is needed and browser is not attached.")
        #                 next_step = "attach_browser_target"
        #         elif not runtime_analysis:
        #             if next_step != "inspect_runtime":
        #                 print(f"Correcting next_step from {next_step} to inspect_runtime because runtime is needed and runtime analysis is missing.")
        #                 next_step = "inspect_runtime"
        #         else:
        #             # 已有 runtime 信息，再考虑动作
        #             if new_task_type == "modify":
        #                 if next_step not in {"modify_code", "search_file", "finish"}:
        #                     print(f"Correcting next_step from {next_step} to modify_code in action phase.")
        #                     next_step = "modify_code"
        #             elif new_task_type == "refactor":
        #                 if next_step not in {"refactor_code", "search_file", "finish"}:
        #                     print(f"Correcting next_step from {next_step} to refactor_code in action phase.")
        #                     next_step = "refactor_code"
        #             elif new_task_type == "debug":
        #                 if next_step not in {"search_file", "inspect_runtime", "finish"}:
        #                     print(f"Correcting next_step from {next_step} to search_file for debug task in action phase.")
        #                     next_step = "search_file"
        #             else:
        #                 if next_step not in {"search_file", "finish"}:
        #                     print(f"Correcting next_step from {next_step} to search_file for search task in action phase.")
        #                     next_step = "search_file"
        #     else:
        #         # 不需要 runtime，按静态分析流走
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
        #         next_step = "inspect_runtime"
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