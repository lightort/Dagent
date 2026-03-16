import json
from state.agent_state import AgentState
from config.model_config import llm


SYSTEM_PROMPT = """
你是一个网页代码分析 Agent 的代码解释节点。
你的任务是根据用户请求、已选文件和代码上下文，解释代码的作用、结构、逻辑和关键点。

你必须只输出 JSON，不能输出任何额外解释、markdown、代码块。

输出格式严格为：
{
  "analysis": "...",
  "final_response": "..."
}

要求：
1. analysis 用于给后续节点作为中间分析，应该简洁但有信息量
2. final_response 用于直接回复用户，应尽量清晰、自然、结构化
3. 如果当前上下文不足以完整解释，也要明确指出缺少什么信息
4. 解释时优先关注：
   - 这个文件/代码块是做什么的
   - 核心函数、组件、状态、流程
   - 输入输出关系
   - 与用户问题最相关的部分
5. 不要编造未出现的逻辑
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


def explain_code_node(state: AgentState) -> AgentState:
    """
    基于 code_context 解释代码
    """
    print("Explaining code by LLM...")

    updated_state = state.copy()
    updated_state["current_step"] = "explain_code"
    updated_state["error"] = None

    try:
        user_request = state.get("user_request", "") or ""
        selected_files = state.get("selected_files", []) or []
        code_context = state.get("code_context", []) or []
        previous_analysis = state.get("analysis", "") or ""
        workspace_summary = state.get("workspace_summary", {}) or {}

        if not code_context:
            updated_state["analysis"] = "当前没有可解释的 code_context，无法进行代码解释。"
            updated_state["final_response"] = "我还没有拿到可供解释的代码内容，因此暂时无法解释具体实现。"
            print("No code context available for explanation.")
            return updated_state

        prompt = f"""
当前用户请求：
{user_request}

当前已选文件：
{json.dumps(selected_files, ensure_ascii=False)}

已有分析：
{previous_analysis}

工作区摘要：
{json.dumps({
    "root": workspace_summary.get("root"),
    "scripts": workspace_summary.get("scripts", []),
    "file_count": len(workspace_summary.get("files", []) or [])
}, ensure_ascii=False)}

代码上下文：
{json.dumps(code_context, ensure_ascii=False)}

请基于以上信息解释代码，输出：
1. analysis：给 Agent 后续使用的中间分析
2. final_response：可以直接回复给用户的解释结果

注意：
- 只解释当前上下文中实际出现的内容
- 如果上下文不足，请明确指出不足
- 只能输出 JSON
"""

        response = llm.invoke([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ])

        content = response.content if hasattr(response, "content") else str(response)
        print("LLM raw response in explain_code:", content)

        result = _safe_json_load(content)

        analysis = (result.get("analysis", "") or "").strip()
        final_response = (result.get("final_response", "") or "").strip()

        if not analysis:
            analysis = "已基于当前代码上下文完成解释。"

        if not final_response:
            final_response = analysis

        updated_state["analysis"] = analysis
        updated_state["final_response"] = final_response

        print("Code explanation completed.")
        return updated_state

    except Exception as e:
        updated_state["error"] = f"Error explaining code: {e}"
        print(updated_state["error"])
        return updated_state