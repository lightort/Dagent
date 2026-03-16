import json
import os
from typing import List

from state.agent_state import AgentState, CodeChunk
from config.model_config import llm


MAX_FILES_TO_READ = 3
MAX_CHARS_PER_CHUNK = 12000
CONTEXT_EXPAND_LINES = 60


SYSTEM_PROMPT = """
你是一个网页代码分析 Agent 的“精读代码”节点。
你的任务是基于用户请求、已选文件和代码上下文，对已经定位到的代码片段进行精读和解释。

你必须只输出 JSON，不能输出任何额外解释、markdown、代码块。

输出格式严格为：
{
  "analysis": "...",
  "final_response": "..."
}

要求：
1. analysis 是给 Agent 后续节点使用的中间分析，简洁但有信息量
2. final_response 是可以直接给用户看的解释结果，表达清楚自然
3. 优先解释和用户请求最相关的代码片段
4. 如果上下文不足，也要明确指出还缺什么
5. 不要编造代码中不存在的逻辑
6. 如果给出的代码片段来自大文件中的局部区域，请重点解释局部逻辑和它在文件中的作用
"""


def _read_text_file(file_path: str) -> str:
    """
    读取文本文件内容，优先用 utf-8，失败后降级
    """
    encodings = ["utf-8", "utf-8-sig", "gbk", "latin-1"]

    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding, errors="replace") as f:
                return f.read()
        except Exception:
            continue

    raise ValueError(f"Unable to read file: {file_path}")


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


def _truncate_content(content: str, max_chars: int = MAX_CHARS_PER_CHUNK) -> str:
    """
    控制单个代码片段长度，避免上下文过大
    """
    if len(content) <= max_chars:
        return content

    head = content[: max_chars // 2]
    tail = content[-max_chars // 2 :]
    return head + "\n\n# ... CONTENT TRUNCATED ...\n\n" + tail


def _make_summary(file_path: str, content: str, start_line: int, end_line: int) -> str:
    """
    基于规则生成一个轻量 summary，供后续 LLM 参考
    """
    lines = content.splitlines()
    line_count = len(lines)
    non_empty_lines = sum(1 for line in lines if line.strip())

    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()

    summary_parts = [
        f"文件名: {filename}",
        f"扩展名: {ext or 'unknown'}",
        f"范围: {start_line}-{end_line}",
        f"片段行数: {line_count}",
        f"非空行数: {non_empty_lines}",
    ]

    content_lower = content.lower()

    if "export default" in content_lower:
        summary_parts.append("疑似默认导出模块")
    if "function " in content_lower or "const " in content_lower or "class " in content_lower or "def " in content_lower:
        summary_parts.append("包含函数/类/变量定义")
    if "useeffect" in content_lower or "usestate" in content_lower or "usememo" in content_lower:
        summary_parts.append("疑似 React 组件逻辑")
    if "<template" in content_lower or "<script" in content_lower:
        summary_parts.append("疑似 Vue 单文件组件")
    if "router" in content_lower or "routes" in content_lower or "route" in content_lower:
        summary_parts.append("疑似路由相关")
    if "fetch(" in content_lower or "axios" in content_lower or "request(" in content_lower:
        summary_parts.append("包含请求逻辑")
    if "form" in content_lower or "input" in content_lower or "button" in content_lower:
        summary_parts.append("疑似界面交互相关")
    if "error" in content_lower or "throw" in content_lower or "catch" in content_lower:
        summary_parts.append("包含错误处理")

    return "；".join(summary_parts)


def _expand_code_context(
    workspace_root: str,
    code_context: List[CodeChunk],
    expand_lines: int = CONTEXT_EXPAND_LINES,
) -> List[CodeChunk]:
    """
    基于 search_in_file 产出的 code_context，回源文件扩展上下文
    """
    expanded_context: List[CodeChunk] = []

    for chunk in code_context:
        file_path = chunk.get("file_path", "")
        if not file_path:
            continue

        abs_path = file_path
        if not os.path.isabs(abs_path):
            abs_path = os.path.join(workspace_root, file_path)

        if not os.path.exists(abs_path) or not os.path.isfile(abs_path):
            print(f"File does not exist or is not a regular file: {abs_path}")
            continue

        content = _read_text_file(abs_path)
        lines = content.splitlines()
        total_lines = len(lines)

        original_start = max(1, int(chunk.get("start_line", 1)))
        original_end = min(total_lines, int(chunk.get("end_line", total_lines)))

        expanded_start = max(1, original_start - expand_lines)
        expanded_end = min(total_lines, original_end + expand_lines)

        expanded_lines = lines[expanded_start - 1 : expanded_end]
        expanded_content = "\n".join(expanded_lines)
        expanded_content = _truncate_content(expanded_content)

        expanded_chunk: CodeChunk = {
            "file_path": file_path,
            "start_line": expanded_start,
            "end_line": expanded_end,
            "content": expanded_content,
            "summary": _make_summary(
                file_path=file_path,
                content="\n".join(expanded_lines),
                start_line=expanded_start,
                end_line=expanded_end,
            ),
        }
        expanded_context.append(expanded_chunk)

    return expanded_context


def _fallback_read_selected_files(
    workspace_root: str,
    selected_files: List[str],
) -> List[CodeChunk]:
    """
    当没有 code_context 时，退回到 selected_files 做兜底读取
    """
    code_context: List[CodeChunk] = []

    files_to_read = selected_files[:MAX_FILES_TO_READ]

    for file_path in files_to_read:
        abs_path = file_path
        if not os.path.isabs(abs_path):
            abs_path = os.path.join(workspace_root, file_path)

        if not os.path.exists(abs_path):
            print(f"File does not exist: {abs_path}")
            continue

        if not os.path.isfile(abs_path):
            print(f"Path is not a file: {abs_path}")
            continue

        content = _read_text_file(abs_path)
        lines = content.splitlines()
        line_count = len(lines)

        truncated_content = _truncate_content(content)

        chunk: CodeChunk = {
            "file_path": file_path,
            "start_line": 1,
            "end_line": line_count,
            "content": truncated_content,
            "summary": _make_summary(
                file_path=file_path,
                content=content,
                start_line=1,
                end_line=line_count,
            ),
        }
        code_context.append(chunk)

    return code_context


def _explain_code_with_llm(
    user_request: str,
    task_type: str,
    selected_files: List[str],
    code_context: List[CodeChunk],
    previous_analysis: str,
) -> tuple[str, str]:
    prompt = f"""
当前用户请求：
{user_request}

当前任务类型：
{task_type}

当前已选文件：
{json.dumps(selected_files, ensure_ascii=False)}

已有分析：
{previous_analysis}

当前精读后的代码上下文：
{json.dumps(code_context, ensure_ascii=False)}

请基于这些信息输出：
1. analysis：给 Agent 后续使用的中间分析
2. final_response：可以直接回复给用户的解释结果

注意：
- 只解释当前上下文中真实出现的内容
- 如果上下文不足，请明确指出不足
- 只能输出 JSON
"""

    response = llm.invoke([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ])

    content = response.content if hasattr(response, "content") else str(response)
    print("LLM raw response in read_file:", content)

    result = _safe_json_load(content)
    analysis = (result.get("analysis", "") or "").strip()
    final_response = (result.get("final_response", "") or "").strip()

    if not analysis:
        analysis = "已基于当前代码上下文完成精读和解释。"
    if not final_response:
        final_response = analysis

    return analysis, final_response


def read_file_node(state: AgentState) -> AgentState:
    """
    精读代码：
    1. 优先基于 search_in_file 产出的 code_context 回源扩展上下文
    2. 若没有 code_context，则退回到 selected_files 兜底读取
    3. 基于精读后的上下文直接生成解释
    """
    print("Reading code context and explaining...")

    updated_state = state.copy()
    updated_state["current_step"] = "read_file"
    updated_state["error"] = None

    try:
        workspace_root = state.get("workspace_root", "") or os.getcwd()
        selected_files = state.get("selected_files", []) or []
        existing_code_context = state.get("code_context", []) or []
        user_request = state.get("user_request", "") or ""
        task_type = state.get("task_type", "") or ""
        previous_analysis = state.get("analysis", "") or ""

        # 优先使用 search_in_file 产出的 code_context
        if existing_code_context:
            refined_code_context = _expand_code_context(
                workspace_root=workspace_root,
                code_context=existing_code_context,
                expand_lines=CONTEXT_EXPAND_LINES,
            )
            source_mode = "expanded_from_code_context"
        else:
            refined_code_context = _fallback_read_selected_files(
                workspace_root=workspace_root,
                selected_files=selected_files,
            )
            source_mode = "fallback_from_selected_files"

        updated_state["code_context"] = refined_code_context

        if not refined_code_context:
            updated_state["analysis"] = "未成功获取任何可精读的代码内容。"
            updated_state["final_response"] = "当前没有成功读取到可供分析的代码内容，因此暂时无法继续解释。"
            print("No readable code context available.")
            return updated_state

        read_summary = (
            f"本轮读取模式: {source_mode}；"
            f"共得到 {len(refined_code_context)} 个代码片段；"
            f"涉及文件: {[chunk['file_path'] for chunk in refined_code_context]}。"
        )

        llm_analysis, final_response = _explain_code_with_llm(
            user_request=user_request,
            task_type=task_type,
            selected_files=selected_files,
            code_context=refined_code_context,
            previous_analysis=previous_analysis,
        )

        updated_state["analysis"] = f"{read_summary} {llm_analysis}"
        updated_state["final_response"] = final_response
        updated_state["search_phase"] = "action"

        print(f"Read completed. Loaded {len(refined_code_context)} refined chunks.")
        return updated_state

    except Exception as e:
        updated_state["error"] = f"Error reading files: {e}"
        print(updated_state["error"])
        return updated_state