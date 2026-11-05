import asyncio

from tests.fakes import ScriptedChatModel, text_message, tool_call_message
from tests.integration.approval_helpers import INCIDENT_ARGS


async def test_waiting_for_approval_does_not_use_up_the_run_time_limit(harness_factory, settings):
    short_limit_settings = settings.model_copy(update={"max_run_seconds": 1})
    chat_model = ScriptedChatModel(
        responses=[
            tool_call_message("create_incident", INCIDENT_ARGS, "call_incident"),
            text_message("Done."),
        ]
    )
    harness = harness_factory(chat_model, settings_override=short_limit_settings)
    paused = await harness.service.start_run("Open an incident")

    await asyncio.sleep(1.3)
    finished = await harness.service.approve(paused["run_id"])

    assert finished["status"] == "COMPLETED"
