'''
user_request:用户原始请求

task_type:当前任务类型（解释代码 / 找 bug / 修改代码 / 重构）

workspace_root:项目根目录

workspace_summary:扫描后的项目概览

candidate_files:可能相关的文件列表

selected_files:当前确定要分析/修改的文件

code_context:提取出来的代码片段

analysis:分析结果

plan:后续执行计划

patches:待应用的修改

final_response:最终输出给用户的结果

current_step:当前执行的流程节点

next_step:流程路由字段

error:错误信息
'''


from typing import TypedDict, Optional, List, Dict, Any


class CodeChunk(TypedDict, total=False):
    file_path: str
    start_line: int
    end_line: int
    content: str
    summary: str


class Patch(TypedDict, total=False):
    file_path: str
    original_content: str
    new_content: str
    diff: str
    reason: str


class AgentState(TypedDict, total=False):
    # 用户请求
    user_request: str
    task_type: str  # explain / debug / modify / refactor / search
    search_phase: str

    # 项目工作区
    workspace_root: str
    workspace_summary: Dict[str, Any]

    # 检索与上下文
    candidate_files: List[str]
    selected_files: List[str]
    code_context: List[CodeChunk]

    # 分析与规划
    analysis: str
    plan: List[str]

    # 修改结果
    patches: List[Patch]

    # 执行控制
    current_step: str
    next_step: str
    error: Optional[str]

    # 输出
    final_response: str