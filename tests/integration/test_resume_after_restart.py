from tests.fakes import ScriptedChatModel, text_message, tool_call_message
from tests.integration.approval_helpers import INCIDENT_ARGS


async def test_paused_run_resumes_with_a_fresh_service(harness_factory):
    first_harness = harness_factory(
        ScriptedChatModel(
            responses=[tool_call_message("create_incident", INCIDENT_ARGS, "call_incident")]
        )
    )
    paused = await first_harness.service.start_run("Open an incident")

    restarted_harness = harness_factory(
        ScriptedChatModel(responses=[text_message("Created after restart.")])
    )
    finished = await restarted_harness.service.approve(paused["run_id"])

    assert finished["status"] == "COMPLETED"
    assert finished["final_answer"] == "Created after restart."
    assert await restarted_harness.incidents.count() == 1
