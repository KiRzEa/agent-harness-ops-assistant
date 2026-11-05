import pytest
from pymongo.errors import DuplicateKeyError

from src.store.events import EventLog, EventType
from src.store.runs import ApprovalRepository, ApprovalStatus, RunRepository


async def test_event_sequence_is_contiguous_per_run(database):
    runs = RunRepository(database)
    events = EventLog(database)
    await runs.create("run-1", "objective")
    await runs.create("run-2", "objective")

    await events.append("run-1", EventType.RUN_STARTED)
    await events.append("run-2", EventType.RUN_STARTED)
    await events.append("run-1", EventType.LLM_CALL, {"step": 1}, duration_ms=12)

    first_run = await events.list_events("run-1")
    assert [event["seq"] for event in first_run] == [1, 2]
    assert first_run[1]["duration_ms"] == 12
    assert [event["seq"] for event in await events.list_events("run-2")] == [1]


async def test_approval_is_created_once_and_decided_once(database):
    approvals = ApprovalRepository(database)
    args = {"title": "t", "description": "d", "severity": "high"}

    first, created_first = await approvals.get_or_create_pending(
        "run-1", "call-1", "create_incident", args
    )
    second, created_second = await approvals.get_or_create_pending(
        "run-1", "call-1", "create_incident", args
    )

    assert created_first and not created_second
    assert first["_id"] == second["_id"]
    assert await approvals.decide(first["_id"], ApprovalStatus.APPROVED) is True
    assert await approvals.decide(first["_id"], ApprovalStatus.REJECTED) is False
    assert (await approvals.get(first["_id"]))["status"] == "APPROVED"


async def test_incident_idempotency_key_is_unique(database):
    await database.incidents.insert_one({"_id": "INC-1", "idempotency_key": "run-1:call-1"})
    with pytest.raises(DuplicateKeyError):
        await database.incidents.insert_one({"_id": "INC-2", "idempotency_key": "run-1:call-1"})
