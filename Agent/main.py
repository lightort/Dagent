from graph.agent_graph import build_graph

graph = build_graph()

result = graph.invoke({
    "input": "帮我查找该网页中Our new site is coming soon!!!的样式定义",
    "user_request": "帮我查找该网页中Our new site is coming soon!!!的样式定义"
})

print(result.get("final_response", "No response found"))
