from config.llm import llm


def llm_node(state):

    user_input = state["input"]

    prompt = f"""
You are an AI agent.

If the question requires calculation,
you MUST respond exactly in this format:

CALCULATE: <math expression>

Example:
CALCULATE: 45 * 3 + 2

Do not solve the problem yourself.

Question: {user_input}
"""

    response = llm.invoke(prompt).content

    print("LLM RESPONSE:", response)

    if "CALCULATE:" in response:
        expression = response.split("CALCULATE:")[-1].strip()
        return {"tool_input": expression}

    return {"result": response}