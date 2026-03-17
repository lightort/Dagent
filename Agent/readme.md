# Agent 项目说明

## 1. 项目结构（当前代码）

```text
Agent/
├─ main.py
├─ readme.md
├─ requirements.txt
├─ config/
│  ├─ model_config.py
│  └─ prompt_config.py
├─ graph/
│  └─ agent_graph.py
├─ nodes/
│  ├─ start_browser.py
│  ├─ scan_workspace.py
│  ├─ analyze_request.py
│  ├─ attach_browser_target.py
│  ├─ runtime_load_page.py
│  ├─ runtime_capture_dom.py
│  ├─ runtime_collect_console.py
│  ├─ runtime_collect_network.py
│  ├─ search_file.py
│  ├─ search_in_file.py
│  ├─ read_file.py
│  └─ check_task_status.py
├─ routers/
│  └─ router.py
├─ state/
│  └─ agent_state.py
├─ tools/
│  ├─ workspace_scanner.py
│  ├─ cdp_target_resolver.py
│  ├─ browser_page_loader.py
│  ├─ dom_snapshot.py
│  ├─ browser_console.py
│  ├─ network_inspector.py
│  └─ runtime_helpers.py
├─ WebPage/
│  ├─ index.html
│  ├─ readme.txt
│  ├─ css/
│  ├─ js/
│  ├─ images/
│  └─ font/
└─ CDP/  (Node.js CLI 与调试能力实现，体量较大，此处省略明细)
```

说明：
- Python Agent 主体在 `config/graph/nodes/routers/state/tools`。
- `WebPage/` 是默认示例页面资源。
- `CDP/` 是底层 CLI 与 Chrome DevTools Protocol 工具层，Python 的部分节点会调用它。

## 2. Agent Graph（以 `graph/agent_graph.py` 为准）

入口：
1. `start_browser`
2. `scan_workspace`
3. `analyze_request`

### `analyze_request` 可路由到
- `attach_browser_target`
- `runtime_load_page`
- `runtime_capture_dom`
- `runtime_collect_console`
- `runtime_collect_network`
- `search_file`
- `search_in_file`
- `read_file`
- `finish` -> `END`
- `error` -> `END`

### 固定边
- `attach_browser_target` -> `analyze_request`
- `runtime_load_page` -> `check_task_status`
- `runtime_capture_dom` -> `check_task_status`
- `runtime_collect_console` -> `check_task_status`
- `runtime_collect_network` -> `check_task_status`
- `search_file` -> `check_task_status`
- `search_in_file` -> `check_task_status`
- `read_file` -> `check_task_status`

### `check_task_status` 可路由到
- `continue` -> `analyze_request`
- `attach_browser_target`
- `runtime_load_page`
- `runtime_capture_dom`
- `runtime_collect_console`
- `runtime_collect_network`
- `done` -> `END`
- `error` -> `END`

## 3. 节点职责

- `start_browser`: 启动 Chrome（远程调试端口 9222），并预安装 console/network 采集缓冲。
- `scan_workspace`: 扫描工作区文件与脚本，写入 `workspace_summary`。
- `analyze_request`: LLM 决策节点，基于状态选择下一步动作。
- `attach_browser_target`: 绑定目标页面，建立 `cdp_session`。
- `runtime_load_page`: 导航并读取页面基础信息（url/title/readyState/html 文件保存路径）。
- `runtime_capture_dom`: 抓取 DOM 与摘要。
- `runtime_collect_console`: 收集 console 日志并摘要。
- `runtime_collect_network`: 收集 network 日志并汇总 runtime 分析。
- `search_file`: 从工作区文件中召回并选择候选文件。
- `search_in_file`: 文件内按 chunk 检索并选择最相关代码片段。
- `read_file`: 扩展上下文后精读代码，产出可直接回答用户的文本。
- `check_task_status`: LLM 状态检查节点，决定继续、跳转或结束。

## 4. 状态与路由约束

- 全局状态定义：`state/agent_state.py` 中的 `AgentState`。
- 关键字段：
  - 规划与控制：`task_type`, `search_phase`, `current_step`, `next_step`, `error`
  - 静态分析：`workspace_summary`, `candidate_files`, `selected_files`, `code_context`
  - 运行时分析：`browser_attached`, `cdp_session`, `runtime_page_meta`, `runtime_dom_summary`, `console_summary`, `network_summary`, `runtime_analysis`
  - 输出：`analysis`, `final_response`
- 路由白名单校验在 `routers/router.py`，非法 `next_step` 会被强制转为 `error`。

## 5. 运行方式（当前入口）

- 入口文件：`main.py`
- 调用方式：构建 graph 后执行 `graph.invoke({...})`
- 最终输出：打印 `final_response`
