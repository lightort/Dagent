| 文件夹     | 作用           |
| ------- | ------------ |
| graph   | 构建 LangGraph |
| nodes   | Agent节点      |
| tools   | 工具实现         |
| routers | 条件路由         |
| state   | 状态定义         |
| config  | 模型配置         |
| main    | 启动程序         |


project/
│
├── main.py
│
├── config/
│   ├── model_config.py
│   └── prompt_config.py
│
├── state/
│   └── agent_state.py
│
├── graph/
│   └── agent_graph.py
│
├── nodes/
│   ├── scan_workspace.py
│   ├── analyze_request.py
│   ├── attach_browser_target.py
│   ├── search_code.py
│   ├── search_in_code.py
│   ├── modify_code.py
│   ├── read_file.py
│   ├── inspect_runtime.py
│   ├── refactor_code.py
│   ├── check_task_status.py
│   └── apply_patch.py
│
├── routers/
│   └── router.py
│
└── tools/
    ├── file_reader.py
    ├── file_writer.py
    ├── workspace_scanner.py
    ├── code_search.py
    ├── diff_tool.py
    ├── path_utils.py
    ├── browser_console.py
    ├── browser_page_loader.py
    ├── cdp_target_resolver.py
    ├── dom_snapshot.py
    ├── network_inspector.py


scan_workspace
      ↓
analyze_request
      ↓
[route_after_analyze]
   ├── attach_browser_target → inspect_runtime → check_task_status
   ├── search_file           → check_task_status
   ├── read_file             → check_task_status
   ├── search_in_file        → check_task_status
   ├── modify_code           → check_task_status
   ├── refactor_code         → check_task_status
   ├── finish                → END
   └── error                 → END

check_task_status
   ├── continue              → analyze_request
   ├── attach_browser_target → attach_browser_target
   ├── inspect_runtime       → inspect_runtime
   ├── apply_patch           → apply_patch
   ├── done                  → END
   └── error                 → END

apply_patch
   ↓
check_task_status