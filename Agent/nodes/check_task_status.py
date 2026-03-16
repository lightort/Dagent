import json
from state.agent_state import AgentState
from config.model_config import llm


SYSTEM_PROMPT = """
你是一个网页代码分析 Agent 的任务状态评估器。
你的职责是根据当前 AgentState 判断当前任务是否已经完成，或者下一步应该继续分析、应用补丁、还是结束。

你必须只输出 JSON，不能输出任何额外解释、markdown、代码块。

你可选择的 next_step 只有：
- continue
- apply_patch
- done

决策原则：
1. 如果当前信息不足以完成任务，则输出 continue
2. 如果已经生成了可应用的 patches，则输出 apply_patch
3. 如果任务目标已经完成，或者已经可以给用户最终答复，则输出 done
4. 只有当确实已经足够回答用户问题时，才输出 done
5. 对 debug 类型任务，如果已经形成清晰分析结论，通常可以 done
6. 对 modify/refactor 类型任务，如果已有 patches 且尚未应用，通常应输出 apply_patch
7. analysis 应简洁说明你的判断依据
8. final_response 只有在 next_step=done 时才应尽量填写；否则可以为空字符串

输出格式必须严格为：
{
  "analysis": "...",
  "next_step": "continue | apply_patch | done",
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
    检查当前任务状态，决定是继续分析、应用补丁还是结束
    """
    print("Checking task status by LLM...")

    updated_state = state.copy()
    updated_state["current_step"] = "check_task_status"
    updated_state["error"] = None

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
        patches = state.get("patches", []) or []
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

patches:
{json.dumps(patches, ensure_ascii=False)}

final_response:
{final_response}

刚刚执行完的节点:
{previous_step}

请判断当前任务状态：
1. 如果还缺少信息，无法完成任务，则 next_step = continue
2. 如果已有明确 patches 且需要进入补丁应用，则 next_step = apply_patch
3. 如果任务已经足够完成，则 next_step = done

注意：
- 对 modify/refactor，如果 patches 非空且明显是待落地修改，优先考虑 apply_patch
- 对 debug，如果已经有足够清晰的 analysis 或 final_response，通常可 done
- 对 search/read 之后，如果只是拿到了文件但还没真正形成结论，通常应 continue
- 只能输出 JSON
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

        valid_next_steps = {"continue", "apply_patch", "done"}
        if next_step not in valid_next_steps:
            raise ValueError(f"Invalid next_step from LLM: {next_step}")

        # 一些安全兜底逻辑，避免明显错误流转
        if next_step == "apply_patch" and not patches:
            print("No patches found, fallback from apply_patch to continue")
            next_step = "continue"
            if not new_analysis:
                new_analysis = "当前尚无可应用的补丁，继续分析。"

        if next_step == "done" and not new_final_response:
            # done 时尽量保证有最终输出
            if task_type == "debug" and analysis:
                new_final_response = analysis
            elif task_type in {"modify", "refactor"} and patches:
                new_final_response = "已完成修改方案生成，可进入补丁应用。"
            else:
                new_final_response = "任务已完成。"

        updated_state["analysis"] = new_analysis or analysis
        updated_state["next_step"] = next_step
        updated_state["final_response"] = new_final_response or final_response

        print(f"Task status checked. next_step={next_step}")
        return updated_state

    except Exception as e:
        updated_state["error"] = f"Error checking task status: {e}"
        print(updated_state["error"])
        return updated_state