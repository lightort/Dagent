from langgraph.graph import END


def router(state):

    print("STATE IN ROUTER:", state)

    tool_input = state.get("tool_input")

    if tool_input:
        print("ROUTING TO CALCULATOR")
        return "calculator"

    print("ROUTING TO END")
    return END