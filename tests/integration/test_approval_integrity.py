import pytest

from src.services.run_service import ApprovalConflictError, RunNotFoundError
from tests.fakes import ScriptedChatModel, text_message, tool_call_message
from tests.integration.approval_helpers import INCIDENT_ARGS


def incident_then_answer():
    return ScriptedChatModel(
        responses=[
            tool_call_message("create_incident", INCIDENT_ARGS, "call_incident"),
            text_message("Done."),
        ]
    )


async def test_second_approval_is_refused_and_creates_no_duplicate(harness_factory):
    harness = harness_factory(incident_then_answer())
    run = await harness.service.start_run("Open an incident")

    await harness.service.approve(run["run_id"])
    with pytest.raises(ApprovalConflictError):
        await harness.service.approve(run["run_id"])

    assert await harness.incidents.count() == 1


async def test_approve_on_run_that_is_not_waiting_is_refused(harness_factory):
    harness = harness_factory(ScriptedChatModel(responses=[text_message("Hi")]))
    run = await harness.service.start_run("Say hi")

    with pytest.raises(ApprovalConflictError):
        await harness.service.approve(run["run_id"])


async def test_approve_unknown_run_raises_not_found(harness_factory):
    harness = harness_factory(ScriptedChatModel())
    with pytest.raises(RunNotFoundError):
        await harness.service.approve("missing")


async def test_changed_arguments_are_never_executed(harness_factory, database):
    harness = harness_factory(incident_then_answer())
    run = await harness.service.start_run("Open an incident")
    await database.approvals.update_one(
        {"run_id": run["run_id"]}, {"$set": {"args.severity": "critical"}}
    )

    finished = await harness.service.approve(run["run_id"])

    assert await harness.incidents.count() == 0
    assert finished["status"] == "COMPLETED"
