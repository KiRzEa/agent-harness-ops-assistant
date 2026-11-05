from datetime import UTC, datetime
from typing import Any

from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError

from src.core.enums import ApprovalStatus


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
            "requested_at": datetime.now(UTC),
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
            {"$set": {"status": decision.value, "decided_at": datetime.now(UTC)}},
        )
        return result.modified_count == 1
