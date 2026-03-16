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
│   ├── search_code.py
│   ├── search_in_code.py
│   ├── find_bug.py
│   ├── modify_code.py
│   ├── refactor_code.py
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
    └── path_utils.py
