from datetime import UTC, datetime
from typing import Any

from pymongo.asynchronous.database import AsyncDatabase

from src.core.enums import RunStatus


class RunRepository:
    def __init__(self, database: AsyncDatabase):
        self._runs = database.runs

    async def ping(self) -> None:
        await self._runs.database.command("ping")

    async def create(self, run_id: str, objective: str) -> None:
        now = datetime.now(UTC)
        await self._runs.insert_one(
            {
                "_id": run_id,
                "objective": objective,
                "status": RunStatus.RUNNING.value,
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
        fields["updated_at"] = datetime.now(UTC)
        await self._runs.update_one({"_id": run_id}, {"$set": fields})
