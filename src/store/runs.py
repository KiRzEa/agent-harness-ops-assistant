from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError


class ApprovalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


def utc_now() -> datetime:
    return datetime.now(UTC)


class RunRepository:
    def __init__(self, database: AsyncDatabase):
        self._runs = database.runs

    async def ping(self) -> None:
        await self._runs.database.command("ping")

    async def create(self, run_id: str, objective: str) -> None:
        now = utc_now()
        await self._runs.insert_one(
            {
                "_id": run_id,
                "objective": objective,
                "status": "RUNNING",
                "step_count": 0,
                "event_seq": 0,
                "created_at": now,
                "updated_at": now,
                "finished_at": None,
                "final_answer": None,
                "error": None,
            }
        )

    async def get(self, run_id: str) -> dict[str, Any] | None:
        return await self._runs.find_one({"_id": run_id})

    async def update(self, run_id: str, **fields: Any) -> None:
        fields["updated_at"] = utc_now()
        await self._runs.update_one({"_id": run_id}, {"$set": fields})


class ApprovalRepository:
    def __init__(self, database: AsyncDatabase):
        self._approvals = database.approvals

    async def get_or_create_pending(
        self, run_id: str, tool_call_id: str, tool_name: str, args: dict[str, Any]
    ) -> tuple[dict[str, Any], bool]:
        filter_by_call = {"run_id": run_id, "tool_call_id": tool_call_id}
        existing = await self._approvals.find_one(filter_by_call)
        if existing:
            return existing, False
        approval = {
            "_id": f"{run_id}:{tool_call_id}",
            **filter_by_call,
            "tool_name": tool_name,
            "args": args,
            "status": ApprovalStatus.PENDING.value,
            "requested_at": utc_now(),
            "decided_at": None,
        }
        try:
            await self._approvals.insert_one(approval)
        except DuplicateKeyError:
            return await self._approvals.find_one(filter_by_call), False
        return approval, True

    async def get(self, approval_id: str) -> dict[str, Any] | None:
        return await self._approvals.find_one({"_id": approval_id})

    async def get_pending_for_run(self, run_id: str) -> dict[str, Any] | None:
        return await self._approvals.find_one(
            {"run_id": run_id, "status": ApprovalStatus.PENDING.value}
        )

    async def decide(self, approval_id: str, decision: ApprovalStatus) -> bool:
        result = await self._approvals.update_one(
            {"_id": approval_id, "status": ApprovalStatus.PENDING.value},
            {"$set": {"status": decision.value, "decided_at": utc_now()}},
        )
        return result.modified_count == 1
