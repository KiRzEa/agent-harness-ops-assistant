from tests.fakes import ScriptedChatModel, many_tool_calls_message, text_message
from tests.integration.approval_helpers import INCIDENT_ARGS


async def test_read_call_runs_first_and_only_incident_waits(harness_factory):
    chat_model = ScriptedChatModel(
        responses=[
            many_tool_calls_message(
                [
                    ("get_service_status", {"service_name": "payments-api"}, "call_status"),
                    ("create_incident", INCIDENT_ARGS, "call_incident"),
                ]
            ),
            text_message("Checked status and opened the incident."),
        ]
    )
    harness = harness_factory(chat_model)

    paused = await harness.service.start_run("Check payments and open an incident if needed")

    assert paused["status"] == "AWAITING_APPROVAL"
    trace_types = [event["type"] for event in await harness.service.get_trace(paused["run_id"])]
    assert "tool_result" in trace_types
    assert await harness.incidents.count() == 0

    finished = await harness.service.approve(paused["run_id"])

    assert finished["status"] == "COMPLETED"
    assert await harness.incidents.count() == 1
    tool_message_ids = [m.tool_call_id for m in chat_model.received_messages[1] if m.type == "tool"]
    assert sorted(tool_message_ids) == ["call_incident", "call_status"]
