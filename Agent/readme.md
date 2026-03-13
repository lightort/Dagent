| 文件夹     | 作用           |
| ------- | ------------ |
| graph   | 构建 LangGraph |
| nodes   | Agent节点      |
| tools   | 工具实现         |
| routers | 条件路由         |
| state   | 状态定义         |
| config  | 模型配置         |
| main    | 启动程序         |


1 main.py
   ↓
2 agent_graph.py 构建Graph
   ↓
3 llm_node.py
   ↓
LLM输出
CALCULATE: 45 * 3 + 2
   ↓
state["tool_input"]
   ↓
4 router.py
   ↓
选择 calculator node
   ↓
5 calculator_node.py
   ↓
6 calculator_tool.py
   ↓
计算
45 * 3 + 2 = 137
   ↓
state["result"]
   ↓
7 main.py 输出
137