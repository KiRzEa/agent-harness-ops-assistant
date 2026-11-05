from src.cli import run_objective
from tests.fakes import ScriptedChatModel, text_message, tool_call_message
from tests.integration.approval_helpers import INCIDENT_ARGS


def incident_script():
    return ScriptedChatModel(
        responses=[
            tool_call_message("create_incident", INCIDENT_ARGS, "call_incident"),
            text_message("Finished."),
        ]
    )


async def test_cli_prompts_and_approves(harness_factory):
    harness = harness_factory(incident_script())
    prompts = []

    def approve_everything(pending_approval):
        prompts.append(pending_approval)
        return True

    run = await run_objective(
        harness.service, "Open an incident", approve_everything, lambda _: None
    )

    assert run["status"] == "COMPLETED"
    assert prompts[0]["args"] == INCIDENT_ARGS
    assert await harness.incidents.count() == 1


async def test_cli_prompt_rejection_creates_nothing(harness_factory):
    harness = harness_factory(incident_script())

    run = await run_objective(harness.service, "Open an incident", lambda _: False, lambda _: None)

    assert run["status"] == "COMPLETED"
    assert await harness.incidents.count() == 0
