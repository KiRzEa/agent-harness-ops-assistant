from tests.fakes import ScriptedChatModel, text_message, tool_call_message
from tests.integration.approval_helpers import INCIDENT_ARGS


async def test_run_pauses_before_creating_incident(harness_factory):
    chat_model = ScriptedChatModel(
        responses=[tool_call_message("create_incident", INCIDENT_ARGS, "call_incident")]
    )
    harness = harness_factory(chat_model)

    run = await harness.service.start_run("Payments is degraded, open an incident")

    assert run["status"] == "AWAITING_APPROVAL"
    assert run["pending_approval"] == {"tool_name": "create_incident", "args": INCIDENT_ARGS}
    assert await harness.incidents.count() == 0
    trace = await harness.service.get_trace(run["run_id"])
    assert [event["type"] for event in trace][-1] == "approval_requested"


async def test_approve_creates_exactly_one_incident_with_approved_args(harness_factory, database):
    chat_model = ScriptedChatModel(
        responses=[
            tool_call_message("create_incident", INCIDENT_ARGS, "call_incident"),
            text_message("Incident created."),
        ]
    )
    harness = harness_factory(chat_model)
    run = await harness.service.start_run("Open an incident")

    finished = await harness.service.approve(run["run_id"])

    assert finished["status"] == "COMPLETED"
    assert finished["pending_approval"] is None
    assert await harness.incidents.count() == 1
    incident = await database.incidents.find_one({})
    assert incident["title"] == INCIDENT_ARGS["title"]
    assert incident["severity"] == "high"
    assert incident["run_id"] == run["run_id"]
    trace_types = [event["type"] for event in await harness.service.get_trace(run["run_id"])]
    assert "approval_decided" in trace_types and "tool_result" in trace_types


async def test_reject_creates_nothing_and_run_still_completes(harness_factory):
    chat_model = ScriptedChatModel(
        responses=[
            tool_call_message("create_incident", INCIDENT_ARGS, "call_incident"),
            text_message("Understood, no incident was opened."),
        ]
    )
    harness = harness_factory(chat_model)
    run = await harness.service.start_run("Open an incident")

    finished = await harness.service.reject(run["run_id"])

    assert finished["status"] == "COMPLETED"
    assert finished["final_answer"] == "Understood, no incident was opened."
    assert await harness.incidents.count() == 0
    model_saw = chat_model.received_messages[1][-1].content
    assert "rejected" in model_saw
    decided = [
        e for e in await harness.service.get_trace(run["run_id"]) if e["type"] == "approval_decided"
    ]
    assert decided[0]["payload"]["decision"] == "REJECTED"
