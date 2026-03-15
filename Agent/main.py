from graph.agent_graph import build_graph

graph = build_graph()

result = graph.invoke({
    "input": "查看工作区目录结构",
    "user_request": "查看工作区目录结构"
})

print(result.get("final_response", "No response found"))
