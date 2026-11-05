import pytest

from src.services.run_service import InvalidObjectiveError, RunNotFoundError
from tests.fakes import ScriptedChatModel, text_message


async def test_objective_without_tools_completes_directly(harness_factory):
    harness = harness_factory(ScriptedChatModel(responses=[text_message("Hello operator.")]))

    run = await harness.service.start_run("Say hello")

    assert run["status"] == "COMPLETED"
    assert run["final_answer"] == "Hello operator."
    trace = await harness.service.get_trace(run["run_id"])
    assert "tool_call" not in [event["type"] for event in trace]


async def test_get_run_returns_stored_result(harness_factory):
    harness = harness_factory(ScriptedChatModel(responses=[text_message("Done.")]))
    run = await harness.service.start_run("Anything")

    stored = await harness.service.get_run(run["run_id"])

    assert stored["status"] == "COMPLETED"
    assert stored["objective"] == "Anything"


async def test_unknown_run_raises(harness_factory):
    harness = harness_factory(ScriptedChatModel())
    with pytest.raises(RunNotFoundError):
        await harness.service.get_run("missing")


@pytest.mark.parametrize("objective", ["", "   ", "x" * 2001])
async def test_invalid_objective_is_rejected(harness_factory, objective):
    harness = harness_factory(ScriptedChatModel())
    with pytest.raises(InvalidObjectiveError):
        await harness.service.start_run(objective)
