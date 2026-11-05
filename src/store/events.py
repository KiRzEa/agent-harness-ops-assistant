from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pymongo import ReturnDocument
from pymongo.asynchronous.database import AsyncDatabase

from src.core.logging import get_logger

logger = get_logger("events")


class EventType(StrEnum):
    RUN_STARTED = "run_started"
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    TOOL_ERROR = "tool_error"
    TOOL_RETRY = "tool_retry"
    VALIDATION_ERROR = "validation_error"
    REPAIR = "repair"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_DECIDED = "approval_decided"
    LIMIT_EXCEEDED = "limit_exceeded"
    RUN_FINISHED = "run_finished"


class EventLog:
    def __init__(self, database: AsyncDatabase):
        self._events = database.events
        self._runs = database.runs

    async def append(
        self,
        run_id: str,
        event_type: EventType,
        payload: dict[str, Any] | None = None,
        duration_ms: int | None = None,
    ) -> int:
        counter = await self._runs.find_one_and_update(
            {"_id": run_id},
            {"$inc": {"event_seq": 1}},
            return_document=ReturnDocument.AFTER,
            projection={"event_seq": 1},
        )
        seq = counter["event_seq"]
        await self._events.insert_one(
            {
                "run_id": run_id,
                "seq": seq,
                "type": event_type.value,
                "payload": payload or {},
                "ts": datetime.now(UTC),
                "duration_ms": duration_ms,
            }
        )
        logger.info(
            event_type.value, run_id=run_id, seq=seq, duration_ms=duration_ms, **(payload or {})
        )
        return seq

    async def list_events(self, run_id: str) -> list[dict[str, Any]]:
        cursor = self._events.find({"run_id": run_id}, {"_id": 0}).sort("seq", 1)
        return await cursor.to_list(length=None)
