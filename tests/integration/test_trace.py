from src.tools.failure_injection import FailureInjector
from tests.fakes import ScriptedChatModel, text_message, tool_call_message
from tests.integration.approval_helpers import INCIDENT_ARGS


async def test_trace_covers_calls_retries_and_approval(harness_factory):
    chat_model = ScriptedChatModel(
        responses=[
            tool_call_message(
                "get_service_status", {"service_name": "auth-service"}, "call_status"
            ),
            tool_call_message("create_incident", INCIDENT_ARGS, "call_incident"),
            text_message("All done."),
        ]
    )
    harness = harness_factory(chat_model, injector=FailureInjector("transient", fail_times=1))
    paused = await harness.service.start_run("Check auth and open an incident")

    paused_view = await harness.service.get_run(paused["run_id"])
    assert paused_view["status"] == "AWAITING_APPROVAL" and paused_view["step_count"] == 2

    await harness.service.approve(paused["run_id"])
    trace = await harness.service.get_trace(paused["run_id"])

    types = [event["type"] for event in trace]
    assert [event["seq"] for event in trace] == list(range(1, len(trace) + 1))
    assert types.count("llm_call") == 3
    assert "tool_retry" in types and "approval_requested" in types and "approval_decided" in types
    assert types[-1] == "run_finished"
    llm_events = [event for event in trace if event["type"] == "llm_call"]
    assert all(event["duration_ms"] is not None for event in llm_events)
    assert all(event["ts"] for event in trace)
