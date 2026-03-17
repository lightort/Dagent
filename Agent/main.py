from graph.agent_graph import build_graph

graph = build_graph()

result = graph.invoke({
    "input": "给我当前网页的网络信息",
    "user_request": "给我当前网页的网络信息",
})

print(result.get("final_response", "No response found"))
