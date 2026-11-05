from langgraph.graph import END

from src.core.enums import RunStatus
from src.graph.state import RunState


def is_running(state: RunState) -> bool:
    return state["status"] == RunStatus.RUNNING.value


def route_after_llm(state: RunState) -> str:
    return "inspect_response" if is_running(state) else END


def route_after_inspect(state: RunState) -> str:
    if not is_running(state):
        return END
    if state["response_problem"]:
        return "repair"
    if state["pending_read_calls"]:
        return "run_read_tools"
    return "request_approval"


def route_after_repair(state: RunState) -> str:
    return "call_llm" if is_running(state) else END


def route_after_read_tools(state: RunState) -> str:
    return "request_approval" if state["pending_incident_call"] else "call_llm"
