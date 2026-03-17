import json
from state.agent_state import AgentState
from config.model_config import llm


SYSTEM_PROMPT = """
你是网页代码分析 Agent 的状态检查节点。
请根据当前状态决定下一步路由。

只允许输出 JSON。

next_step 只能是：
- continue
- attach_browser_target
- runtime_load_page
- runtime_capture_dom
- runtime_collect_console
- runtime_collect_network
- done

决策建议：
1. 信息不足时优先 continue（回到 analyze_request 决策）。
2. 明确需要浏览器绑定时可返回 attach_browser_target。
3. 已绑定浏览器且明确需要运行时子能力时可返回对应 runtime_* 节点。
4. 仅在已可回答用户请求时返回 done。
5. analysis 简洁说明理由。
6. next_step=done 时应尽量给出 final_response。

输出格式：
{
  "analysis": "...",
  "next_step": "...",
  "final_response": "..."
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


def check_task_status_node(state: AgentState) -> AgentState:
    """
    检查当前任务状态，决定继续决策、跳转运行时节点或结束。
    """
    print("Checking task status by LLM...")

    updated_state = state.copy()
    updated_state["current_step"] = "check_task_status"
    updated_state["error"] = None
    updated_state["last_step"] = state.get("current_step", "")

    try:
        user_request = state.get("user_request", "") or ""
        task_type = state.get("task_type", "") or ""
        workspace_root = state.get("workspace_root", "") or ""
        workspace_summary = state.get("workspace_summary", {}) or {}

        candidate_files = state.get("candidate_files", []) or []
        selected_files = state.get("selected_files", []) or []
        code_context = state.get("code_context", []) or []

        analysis = state.get("analysis", "") or ""
        plan = state.get("plan", []) or []
        final_response = state.get("final_response", "") or ""
        previous_step = state.get("current_step", "") or ""

        prompt = f"""
当前 AgentState 关键信息如下：

user_request:
{user_request}

task_type:
{task_type}

workspace_root:
{workspace_root}

workspace_summary:
{json.dumps({
    "root": workspace_summary.get("root"),
    "file_count": len(workspace_summary.get("files", []) or []),
    "scripts": workspace_summary.get("scripts", []),
}, ensure_ascii=False)}

candidate_files:
{json.dumps(candidate_files, ensure_ascii=False)}

selected_files:
{json.dumps(selected_files, ensure_ascii=False)}

code_context:
{json.dumps(code_context, ensure_ascii=False)}

analysis:
{analysis}

plan:
{json.dumps(plan, ensure_ascii=False)}

final_response:
{final_response}

刚执行完的节点:
{previous_step}

请输出：
1. analysis
2. next_step
3. final_response

仅输出 JSON。
"""

        response = llm.invoke([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ])

        content = response.content if hasattr(response, "content") else str(response)
        print("LLM raw response in check_task_status:", content)

        result = _safe_json_load(content)

        new_analysis = (result.get("analysis", "") or "").strip()
        next_step = (result.get("next_step", "") or "").strip()
        new_final_response = (result.get("final_response", "") or "").strip()

        valid_next_steps = {
            "continue",
            "attach_browser_target",
            "runtime_load_page",
            "runtime_capture_dom",
            "runtime_collect_console",
            "runtime_collect_network",
            "done",
        }
        if next_step not in valid_next_steps:
            raise ValueError(f"Invalid next_step from LLM: {next_step}")

        if next_step == "done" and not new_final_response:
            if analysis:
                new_final_response = analysis
            else:
                new_final_response = "任务已完成。"

        updated_state["analysis"] = new_analysis or analysis
        updated_state["next_step"] = next_step
        updated_state["final_response"] = new_final_response or final_response
        updated_state["operation_history"] = state.get("operation_history", []) + ["check_task_status"]

        print(f"Task status checked. next_step={next_step}")
        return updated_state

    except Exception as e:
        updated_state["error"] = f"Error checking task status: {e}"
        print(updated_state["error"])
        return updated_state
