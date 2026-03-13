from graph.agent_graph import build_graph

graph = build_graph()

result = graph.invoke({
    "input": ""
})

print(result["result"])