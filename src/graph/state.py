from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class RunState(TypedDict):
    run_id: str
    messages: Annotated[list[AnyMessage], add_messages]
    step_count: int
    active_seconds: float
    repair_count: int
    status: str
    final_answer: str | None
    error: dict[str, str] | None
    response_problem: str | None
    pending_read_calls: list[dict[str, Any]]
    pending_incident_call: dict[str, Any] | None
