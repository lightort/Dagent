from typing import TypedDict, Optional, List, Dict, Any


class CodeChunk(TypedDict, total=False):
    file_path: str
    start_line: int
    end_line: int
    content: str
    summary: str



class RuntimePageMeta(TypedDict, total=False):
    url: str
    title: str
    ready_state: str
    html_length: int


class ConsoleLog(TypedDict, total=False):
    level: str
    message: str
    source: str
    timestamp: str


class NetworkLog(TypedDict, total=False):
    url: str
    method: str
    status: int
    resource_type: str
    error: str
    timestamp: str


class CDPTargetInfo(TypedDict, total=False):
    id: str
    title: str
    url: str
    type: str
    webSocketDebuggerUrl: str


class AgentState(TypedDict, total=False):
    # 用户请求
    user_request: str
    task_type: str   # search / attach browser
    search_phase: str

    # 项目工作区
    workspace_root: str
    workspace_summary: Dict[str, Any]

    # 检索与上下文
    candidate_files: List[str]
    selected_files: List[str]
    code_context: List[CodeChunk]

    # 浏览器/CDP 连接信息
    remote_debugging_url: str          # 例如: http://127.0.0.1:9222
    target_url: str                    # 例如: file:///C:/Users/.../index.html
    cdp_session: Any
    cdp_target_info: CDPTargetInfo
    browser_attached: bool
    needs_runtime_inspection: bool

    # 运行时页面信息
    runtime_page_meta: RuntimePageMeta
    runtime_dom: str
    runtime_dom_summary: str
    console_logs: List[ConsoleLog]
    console_summary: str
    network_logs: List[NetworkLog]
    network_summary: str
    runtime_analysis: str

    # 分析与规划
    analysis: str
    plan: List[str]


    # 执行控制
    last_step : str 
    current_step: str
    next_step: str
    error: Optional[str]

    # 输出
    final_response: str