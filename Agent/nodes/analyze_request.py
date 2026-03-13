from tools.calculator_tool import calculator


def calculator_node(state):

    expression = state["tool_input"]

    print("CALCULATOR RUNNING:", expression)

    result = eval(expression)

    return {"result": str(result)}