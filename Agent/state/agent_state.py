from typing import TypedDict, Optional


class AgentState(TypedDict):
    input: str
    tool_input: Optional[str]
    result: Optional[str]