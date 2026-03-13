from graph.agent_graph import build_graph

graph = build_graph()

result = graph.invoke({
    "input": "What is 45 * 3 + 2?"
})

print(result["result"])