from graph.agent_graph import build_graph

graph = build_graph()

result = graph.invoke({
    "input": "给我当前网页的Our new site is coming soon!!!的样式",
    "user_request": "给我当前网页的Our new site is coming soon!!!的样式",
})

print(result.get("final_response", "No response found"))
