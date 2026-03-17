import json
import os
import re
from typing import List, Dict, Any

from state.agent_state import AgentState, CodeChunk
from config.model_config import llm


CHUNK_SIZE = 120
CHUNK_OVERLAP = 20
MAX_RECALL_CHUNKS = 20
MAX_SELECTED_CHUNKS = 5

CSS_EXTENSIONS = {".css", ".scss", ".less"}

SYSTEM_PROMPT = """
你是一个网页代码分析 Agent 的文件内代码检索器。
你的任务是根据用户请求、任务类型、已有分析和候选代码片段，从中挑选最相关的代码片段。

你必须只输出 JSON，不能输出任何额外解释、markdown、代码块。

输出格式严格为：
{
  "analysis": "...",
  "selected_chunk_ids": ["chunk_1", "chunk_2"]
}

要求：
1. 你只能从提供的 chunk 列表中选择
2. 选择最相关的代码片段，最多 5 个
3. 优先选择真正与用户问题有关的逻辑，而不是只看名字表面相似
4. 如果需要连续上下文，可以选择多个相邻 chunk
5. analysis 要简洁说明选择依据
"""


STOPWORDS = {
    "the", "a", "an", "to", "for", "of", "in", "on", "at", "by", "with",
    "and", "or", "is", "are", "be", "this", "that",
    "查看", "看看", "分析", "解释", "说明", "代码", "文件", "内容",
    "帮我", "帮忙", "一下", "一个", "这个", "那个", "针对", "进行",
    "请", "一下子", "一下下", "找到", "定位", "样式", "代码里", "这里"
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


def _read_text_file(file_path: str) -> str:
    encodings = ["utf-8", "utf-8-sig", "gbk", "latin-1"]
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding, errors="replace") as f:
                return f.read()
        except Exception:
            continue
    raise ValueError(f"Unable to read file: {file_path}")


def _extract_terms(text: str) -> List[str]:
    text = (text or "").lower().strip()
    raw_terms = re.findall(r"[a-zA-Z0-9_\-./#:%]+|[\u4e00-\u9fff]+", text)

    terms = []
    for term in raw_terms:
        term = term.strip().lower()
        if not term or term in STOPWORDS:
            continue
        if len(term) == 1:
            continue
        terms.append(term)

    seen = set()
    result = []
    for term in terms:
        if term not in seen:
            seen.add(term)
            result.append(term)
    return result


def _split_identifier_tokens(value: str) -> List[str]:
    value = value.strip().lower()
    parts = re.split(r"[^a-zA-Z0-9]+", value)
    return [p for p in parts if p and len(p) > 1]


def _extract_css_chunk_features(content: str) -> Dict[str, List[str]]:
    """
    提取 CSS/SCSS/LESS chunk 的结构化特征
    """
    selectors: List[str] = []
    properties: List[str] = []
    at_rules: List[str] = []
    states: List[str] = []
    tokens: List[str] = []

    # 1. 提取 at-rules，例如 @media / @keyframes / @supports
    at_rule_matches = re.findall(r"@([a-zA-Z\-]+)", content)
    for item in at_rule_matches:
        at_rules.append(f"@{item.lower()}")

    # 2. 提取属性名，例如 width: / background-color:
    property_matches = re.findall(r"(?m)^\s*([a-zA-Z\-]+)\s*:", content)
    for prop in property_matches:
        properties.append(prop.lower())

    # 3. 提取选择器块头
    # 粗略匹配 “selector {”
    selector_matches = re.findall(r"(?ms)([^\{\}]+)\{", content)
    for raw in selector_matches:
        selector = raw.strip()
        if not selector:
            continue

        # 过滤明显不是 selector 的内容
        if selector.startswith("@"):
            continue

        selector = re.sub(r"\s+", " ", selector)
        if len(selector) > 200:
            continue

        # 可能有逗号分隔
        parts = [p.strip() for p in selector.split(",") if p.strip()]
        for part in parts:
            if len(part) <= 200:
                selectors.append(part.lower())

    # 4. 提取状态/伪类/伪元素
    state_matches = re.findall(r"(:{1,2}[a-zA-Z\-]+)", content)
    for state in state_matches:
        states.append(state.lower())

    # 5. 从 selectors 里提取 token
    for selector in selectors:
        cleaned = selector.replace(".", " ").replace("#", " ").replace(":", " ").replace(">", " ")
        cleaned = cleaned.replace("+", " ").replace("~", " ").replace("[", " ").replace("]", " ")
        cleaned = cleaned.replace("=", " ").replace('"', " ").replace("'", " ")
        tokens.extend(_split_identifier_tokens(cleaned))

    # 6. 从 CSS 变量里提取 token
    css_var_matches = re.findall(r"var\(\s*(--[a-zA-Z0-9\-_]+)\s*\)", content)
    for item in css_var_matches:
        tokens.extend(_split_identifier_tokens(item))

    # 7. 从 class/id 名中提取 token
    class_id_matches = re.findall(r"[.#]([a-zA-Z0-9\-_]+)", content)
    for item in class_id_matches:
        tokens.extend(_split_identifier_tokens(item))

    def dedupe_keep_order(items: List[str], limit: int = 30) -> List[str]:
        seen = set()
        result = []
        for item in items:
            item = item.strip().lower()
            if not item or item in seen:
                continue
            seen.add(item)
            result.append(item)
            if len(result) >= limit:
                break
        return result

    return {
        "selectors": dedupe_keep_order(selectors, 20),
        "properties": dedupe_keep_order(properties, 25),
        "at_rules": dedupe_keep_order(at_rules, 10),
        "states": dedupe_keep_order(states, 15),
        "tokens": dedupe_keep_order(tokens, 30),
    }


def _extract_general_chunk_features(content: str) -> Dict[str, List[str]]:
    content_lower = content.lower()

    symbols = re.findall(r"\b(?:function|class|def|const|let|var)\s+([a-zA-Z_][a-zA-Z0-9_]*)", content)
    imports = re.findall(r"\bimport\s+.*?from\s+['\"]([^'\"]+)['\"]", content)
    tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", content_lower)

    def dedupe_keep_order(items: List[str], limit: int = 30) -> List[str]:
        seen = set()
        result = []
        for item in items:
            item = item.strip().lower()
            if not item or item in seen:
                continue
            seen.add(item)
            result.append(item)
            if len(result) >= limit:
                break
        return result

    return {
        "symbols": dedupe_keep_order(symbols, 20),
        "imports": dedupe_keep_order(imports, 20),
        "tokens": dedupe_keep_order(tokens, 30),
    }


def _make_css_chunk_summary(
    file_path: str,
    start_line: int,
    end_line: int,
    features: Dict[str, List[str]]
) -> str:
    selectors = features.get("selectors", [])[:5]
    properties = features.get("properties", [])[:8]
    at_rules = features.get("at_rules", [])[:4]
    states = features.get("states", [])[:6]
    tokens = features.get("tokens", [])[:8]

    parts = [f"{os.path.basename(file_path)}:{start_line}-{end_line}"]

    if selectors:
        parts.append(f"选择器: {', '.join(selectors)}")
    if properties:
        parts.append(f"属性: {', '.join(properties)}")
    if states:
        parts.append(f"状态: {', '.join(states)}")
    if at_rules:
        parts.append(f"规则: {', '.join(at_rules)}")
    if tokens:
        parts.append(f"关键词: {', '.join(tokens)}")

    return "；".join(parts)


def _make_general_chunk_summary(
    file_path: str,
    start_line: int,
    end_line: int,
    content: str,
    features: Dict[str, List[str]]
) -> str:
    content_lower = content.lower()
    parts = [f"{os.path.basename(file_path)}:{start_line}-{end_line}"]

    signals = []
    if "function " in content_lower or "=>" in content_lower:
        signals.append("包含函数逻辑")
    if "class " in content_lower:
        signals.append("包含类定义")
    if "useeffect" in content_lower or "usestate" in content_lower or "usememo" in content_lower:
        signals.append("包含 React hooks")
    if "return (" in content_lower or "<div" in content_lower or "<template" in content_lower:
        signals.append("包含界面渲染")
    if "fetch(" in content_lower or "axios" in content_lower or "request(" in content_lower:
        signals.append("包含请求逻辑")
    if "if " in content_lower or "try:" in content_lower or "catch" in content_lower:
        signals.append("包含条件/异常处理")
    if "router" in content_lower or "route" in content_lower:
        signals.append("包含路由相关")
    if "form" in content_lower or "button" in content_lower or "input" in content_lower:
        signals.append("包含表单/交互")
    if "error" in content_lower or "throw" in content_lower:
        signals.append("包含错误处理")

    if signals:
        parts.append("信号: " + ", ".join(signals[:5]))

    symbols = features.get("symbols", [])[:6]
    imports = features.get("imports", [])[:4]
    tokens = features.get("tokens", [])[:8]

    if symbols:
        parts.append("符号: " + ", ".join(symbols))
    if imports:
        parts.append("导入: " + ", ".join(imports))
    if tokens:
        parts.append("关键词: " + ", ".join(tokens))

    return "；".join(parts)


def _chunk_lines(file_path: str, content: str) -> List[Dict[str, Any]]:
    lines = content.splitlines()
    chunks = []

    if not lines:
        return []

    _, ext = os.path.splitext(file_path.lower())
    is_css_like = ext in CSS_EXTENSIONS

    step = max(1, CHUNK_SIZE - CHUNK_OVERLAP)
    idx = 0
    chunk_index = 0

    while idx < len(lines):
        start = idx
        end = min(idx + CHUNK_SIZE, len(lines))
        chunk_lines = lines[start:end]
        chunk_content = "\n".join(chunk_lines)

        chunk: Dict[str, Any] = {
            "chunk_id": f"{file_path}::chunk_{chunk_index}",
            "file_path": file_path,
            "start_line": start + 1,
            "end_line": end,
            "content": chunk_content,
        }

        if is_css_like:
            css_features = _extract_css_chunk_features(chunk_content)
            chunk.update(css_features)
            chunk["summary"] = _make_css_chunk_summary(file_path, start + 1, end, css_features)
        else:
            general_features = _extract_general_chunk_features(chunk_content)
            chunk.update(general_features)
            chunk["summary"] = _make_general_chunk_summary(file_path, start + 1, end, chunk_content, general_features)

        chunks.append(chunk)

        idx += step
        chunk_index += 1

    return chunks


def _score_css_chunk(chunk: Dict[str, Any], terms: List[str]) -> int:
    score = 0

    file_path = chunk["file_path"].lower()
    summary = chunk["summary"].lower()
    content = chunk["content"].lower()
    selectors = [x.lower() for x in chunk.get("selectors", [])]
    properties = [x.lower() for x in chunk.get("properties", [])]
    at_rules = [x.lower() for x in chunk.get("at_rules", [])]
    states = [x.lower() for x in chunk.get("states", [])]
    tokens = [x.lower() for x in chunk.get("tokens", [])]

    selector_text = " ".join(selectors)
    property_text = " ".join(properties)
    state_text = " ".join(states)
    at_rule_text = " ".join(at_rules)
    token_text = " ".join(tokens)

    for term in terms:
        if term in file_path:
            score += 4
        if term in summary:
            score += 5
        if term in selector_text:
            score += 12
        if term in property_text:
            score += 10
        if term in state_text:
            score += 9
        if term in at_rule_text:
            score += 8
        if term in token_text:
            score += 7
        if term in content:
            score += 3

    # 一些 CSS 相关信号加权
    if selectors:
        score += 1
    if properties:
        score += 1
    if any(x in states for x in [":hover", ":focus", ":active", ":disabled"]):
        score += 1
    if "@media" in at_rules:
        score += 1

    return score


def _score_general_chunk(chunk: Dict[str, Any], terms: List[str]) -> int:
    score = 0
    content = chunk["content"].lower()
    summary = chunk["summary"].lower()
    file_path = chunk["file_path"].lower()

    tokens = [x.lower() for x in chunk.get("tokens", [])]
    symbols = [x.lower() for x in chunk.get("symbols", [])]
    imports = [x.lower() for x in chunk.get("imports", [])]

    token_text = " ".join(tokens)
    symbol_text = " ".join(symbols)
    import_text = " ".join(imports)

    for term in terms:
        if term in file_path:
            score += 5
        if term in summary:
            score += 6
        if term in symbol_text:
            score += 9
        if term in import_text:
            score += 6
        if term in token_text:
            score += 5
        if term in content:
            score += 10

    if any(k in content for k in ["function ", "class ", "const ", "def "]):
        score += 1
    if any(k in content for k in ["useeffect", "usestate", "fetch(", "axios", "router"]):
        score += 2

    return score


def _score_chunk(chunk: Dict[str, Any], terms: List[str]) -> int:
    _, ext = os.path.splitext(chunk["file_path"].lower())
    if ext in CSS_EXTENSIONS:
        return _score_css_chunk(chunk, terms)
    return _score_general_chunk(chunk, terms)


def _recall_chunks(all_chunks: List[Dict[str, Any]], query_text: str, analysis: str) -> List[Dict[str, Any]]:
    terms = _extract_terms(query_text) + _extract_terms(analysis)

    scored = []
    for chunk in all_chunks:
        score = _score_chunk(chunk, terms)
        if score > 0:
            scored.append((chunk, score))

    if not scored:
        return all_chunks[:MAX_RECALL_CHUNKS]

    scored.sort(key=lambda x: (-x[1], x[0]["file_path"], x[0]["start_line"]))
    return [item[0] for item in scored[:MAX_RECALL_CHUNKS]]


def search_in_file_node(state: AgentState) -> AgentState:
    """
    在 selected_files 内部进行代码片段检索（RAG 风格）
    """
    print("Searching inside files by chunk retrieval + LLM reranking...")

    updated_state = state.copy()
    updated_state["current_step"] = "search_in_file"
    updated_state["last_step"] = state.get("current_step", "")
    updated_state["error"] = None

    try:
        workspace_root = state.get("workspace_root", "") or os.getcwd()
        user_request = state.get("user_request", "") or ""
        task_type = state.get("task_type", "") or ""
        selected_files = state.get("selected_files", []) or []
        previous_analysis = state.get("analysis", "") or ""

        if not selected_files:
            updated_state["code_context"] = []
            updated_state["analysis"] = "当前没有 selected_files，无法进行文件内检索。"
            return updated_state

        all_chunks: List[Dict[str, Any]] = []

        for file_path in selected_files:
            abs_path = file_path
            if not os.path.isabs(abs_path):
                abs_path = os.path.join(workspace_root, file_path)

            if not os.path.exists(abs_path) or not os.path.isfile(abs_path):
                continue

            content = _read_text_file(abs_path)
            file_chunks = _chunk_lines(file_path, content)
            all_chunks.extend(file_chunks)

        if not all_chunks:
            updated_state["code_context"] = []
            updated_state["analysis"] = "未能从 selected_files 中切分出任何代码片段。"
            return updated_state

        recalled_chunks = _recall_chunks(all_chunks, user_request, previous_analysis)

        llm_input_chunks = []
        for chunk in recalled_chunks:
            llm_input_chunks.append({
                "chunk_id": chunk["chunk_id"],
                "file_path": chunk["file_path"],
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
                "summary": chunk["summary"],
                "preview": chunk["content"][:1200]
            })

        prompt = f"""
当前用户请求：
{user_request}

当前任务类型：
{task_type}

已有分析：
{previous_analysis}

当前已选文件：
{json.dumps(selected_files, ensure_ascii=False)}

以下是召回后的候选代码片段：
{json.dumps(llm_input_chunks, ensure_ascii=False)}

请从中挑选最相关的代码片段。
输出：
1. analysis：说明为什么这些片段相关
2. selected_chunk_ids：你选择的 chunk_id 列表，最多 5 个

注意：
- 你只能从给出的 chunk_id 中选择
- 优先选择最能帮助解释/定位/修改任务的片段
- 如果需要连续上下文，可以选择相邻 chunk
- 只能输出 JSON
"""

        response = llm.invoke([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ])

        content = response.content if hasattr(response, "content") else str(response)
        print("LLM raw response in search_in_file:", content)

        result = _safe_json_load(content)
        selected_chunk_ids = result.get("selected_chunk_ids", []) or []
        analysis = (result.get("analysis", "") or "").strip()

        recalled_map = {chunk["chunk_id"]: chunk for chunk in recalled_chunks}
        selected_chunks = [recalled_map[cid] for cid in selected_chunk_ids if cid in recalled_map][:MAX_SELECTED_CHUNKS]

        if not selected_chunks:
            selected_chunks = recalled_chunks[: min(MAX_SELECTED_CHUNKS, len(recalled_chunks))]
            if not analysis:
                analysis = "LLM 未明确选出片段，已使用召回结果中的前几个片段作为保底。"

        code_context: List[CodeChunk] = []
        for chunk in selected_chunks:
            code_context.append({
                "file_path": chunk["file_path"],
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
                "content": chunk["content"],
                "summary": chunk["summary"],
            })

        updated_state["code_context"] = code_context
        updated_state["search_phase"] = "read"
        updated_state["analysis"] = analysis or f"已从 {len(selected_files)} 个文件中检索出 {len(code_context)} 个相关代码片段。"

        print(f"search_in_file completed. Selected {len(code_context)} chunks.")
        return updated_state

    except Exception as e:
        updated_state["error"] = f"Error searching inside files: {e}"
        print(updated_state["error"])
        return updated_state