import json
import os
import re
from state.agent_state import AgentState
from config.model_config import llm


MAX_RECALL_FILES = 50
MAX_CANDIDATE_FILES = 10
MAX_SELECTED_FILES = 3


SYSTEM_PROMPT = """
你是一个网页代码分析 Agent 的文件选择器。
你的任务是根据用户请求、任务类型、工作区摘要和文件列表，从候选文件中选出最相关的文件。

你必须只输出 JSON，不能输出任何额外解释、markdown、代码块。

输出格式严格为：
{
  "analysis": "...",
  "candidate_files": ["..."],
  "selected_files": ["..."]
}

要求：
1. candidate_files 表示可能相关的文件，最多 10 个
2. selected_files 表示下一步最值得重点阅读的文件，最多 3 个
3. selected_files 必须是 candidate_files 的子集
4. 优先选择真正可能与用户目标相关的文件，而不是仅仅名字相似
5. 如果没有明显相关文件，可以返回空数组，但 analysis 必须说明原因
"""


STOPWORDS = {
    "the", "a", "an", "to", "for", "of", "in", "on", "at", "by", "with",
    "and", "or", "is", "are", "be", "this", "that",
    "查看", "看看", "分析", "解释", "说明", "代码", "文件", "内容",
    "帮我", "帮忙", "一下", "一个", "这个", "那个", "针对", "进行"
}


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


def _extract_terms(user_request: str) -> list[str]:
    text = (user_request or "").lower().strip()
    raw_terms = re.findall(r"[a-zA-Z0-9_\-./]+|[\u4e00-\u9fff]+", text)

    terms = []
    for term in raw_terms:
        term = term.strip().lower()
        if not term or term in STOPWORDS:
            continue
        terms.append(term)

    seen = set()
    result = []
    for term in terms:
        if term not in seen:
            seen.add(term)
            result.append(term)
    return result


def _recall_files(files: list[str], user_request: str) -> list[str]:
    """
    先做轻量召回，把全量文件缩到一个 LLM 可处理的范围
    """
    terms = _extract_terms(user_request)
    scored = []

    for file_path in files:
        normalized = file_path.replace("\\", "/").lower()
        filename = os.path.basename(normalized)

        score = 0

        for term in terms:
            if term in normalized:
                score += 5
            if term in filename:
                score += 8

        if any(key in normalized for key in ["/src/", "/pages/", "/components/", "/views/", "/app/"]):
            score += 1

        if score > 0:
            scored.append((file_path, score))

    # 如果一个都没召回，就退化为前面一部分文件，避免 LLM 完全没材料
    if not scored:
        return files[:MAX_RECALL_FILES]

    scored.sort(key=lambda x: (-x[1], len(x[0])))
    return [item[0] for item in scored[:MAX_RECALL_FILES]]


def search_file_node(state: AgentState) -> AgentState:
    """
    先召回候选文件，再用 LLM 选择最相关文件
    """
    print("Searching relevant files by recall + LLM ranking...")

    updated_state = state.copy()
    updated_state["current_step"] = "search_file"
    updated_state["last_step"] = state.get("current_step", "")
    updated_state["error"] = None

    try:
        user_request = state.get("user_request", "") or ""
        task_type = state.get("task_type", "") or ""
        workspace_summary = state.get("workspace_summary", {}) or {}
        files = workspace_summary.get("files", []) or []
        previous_analysis = state.get("analysis", "") or []

        if not files:
            updated_state["candidate_files"] = []
            updated_state["selected_files"] = []
            updated_state["analysis"] = "工作区中没有可搜索文件，或扫描结果为空。"
            return updated_state

        recalled_files = _recall_files(files, user_request)

        prompt = f"""
当前用户请求：
{user_request}

当前任务类型：
{task_type}

已有分析：
{previous_analysis}

工作区摘要：
{json.dumps({
    "root": workspace_summary.get("root"),
    "file_count": len(files),
    "scripts": workspace_summary.get("scripts", []),
}, ensure_ascii=False)}

召回后的候选文件列表：
{json.dumps(recalled_files, ensure_ascii=False)}

请从这些文件中判断：
1. 哪些是可能相关的 candidate_files（最多 3 个）
2. 哪些是下一步最值得重点阅读的 selected_files（最多 1 个）
3. 给出简洁 analysis
4.candidate_files和selected_files的格式应该严格为["绝对路径/文件名"]，不得在文件名前后添加任何多余的字符

注意：
- selected_files 必须是 candidate_files 的子集
- 重点考虑语义相关性，不要只看名字表面相似
- 如果请求更像“解释某个页面/功能”，优先选择入口文件、页面文件、组件文件
- 如果请求更像“找 bug / 修改 / 重构”，优先选择最可能承载逻辑的文件
- 只能输出 JSON
"""

        response = llm.invoke([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ])

        content = response.content if hasattr(response, "content") else str(response)
        print("LLM raw response in search_file:", content)

        result = _safe_json_load(content)

        candidate_files = result.get("candidate_files", []) or []
        selected_files = result.get("selected_files", []) or []
        analysis = (result.get("analysis", "") or "").strip()

        # 清洗与校验
        recalled_set = set(recalled_files)
        candidate_files = [f for f in candidate_files if f in recalled_set][:MAX_CANDIDATE_FILES]

        candidate_set = set(candidate_files)
        selected_files = [f for f in selected_files if f in candidate_set][:MAX_SELECTED_FILES]

        # 兜底：如果 LLM 没选 selected_files，但选了 candidate_files，就默认挑前 1~3 个
        if not selected_files and candidate_files:
            selected_files = candidate_files[:MAX_SELECTED_FILES]

        # 再兜底：如果 candidate_files 都没给，但 recalled_files 有，就给一个保底结果
        if not candidate_files and recalled_files:
            candidate_files = recalled_files[:MAX_CANDIDATE_FILES]
            if not selected_files:
                selected_files = candidate_files[:MAX_SELECTED_FILES]
            if not analysis:
                analysis = "LLM 未明确返回候选文件，已使用召回结果作为保底候选。"

        updated_state["candidate_files"] = candidate_files
        updated_state["selected_files"] = selected_files
        updated_state["analysis"] = analysis or "已完成候选文件筛选。"
        updated_state["search_phase"] = "chunk"

        print(f"Search completed. candidate_files={len(candidate_files)}, selected_files={len(selected_files)}")
        return updated_state

    except Exception as e:
        updated_state["error"] = f"Error searching files: {e}"
        print(updated_state["error"])
        return updated_state