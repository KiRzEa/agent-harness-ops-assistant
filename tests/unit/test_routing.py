from langgraph.graph import END

from src.graph.routing import (
    route_after_inspect,
    route_after_llm,
    route_after_read_tools,
    route_after_repair,
)


def state(**overrides):
    base = {
        "status": "RUNNING",
        "response_problem": None,
        "pending_read_calls": [],
        "pending_incident_call": None,
    }
    return {**base, **overrides}


def test_routing_stops_when_run_is_not_running():
    assert route_after_llm(state(status="LIMIT_EXCEEDED")) == END
    assert route_after_inspect(state(status="COMPLETED")) == END
    assert route_after_repair(state(status="FAILED")) == END


def test_routing_follows_the_response_contents():
    assert route_after_llm(state()) == "inspect_response"
    assert route_after_inspect(state(response_problem="empty")) == "repair"
    assert route_after_inspect(state(pending_read_calls=[{"id": "call"}])) == "run_read_tools"
    assert route_after_inspect(state(pending_incident_call={"id": "call"})) == "request_approval"
    assert route_after_repair(state()) == "call_llm"
    assert route_after_read_tools(state(pending_incident_call={"id": "call"})) == "request_approval"
    assert route_after_read_tools(state()) == "call_llm"
