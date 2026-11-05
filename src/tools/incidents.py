import uuid
from datetime import UTC, datetime

from pymongo.asynchronous.database import AsyncDatabase

from src.tools.failure_injection import FailureInjector
from src.tools.schemas import CreateIncidentInput


class IncidentRepository:
    def __init__(self, database: AsyncDatabase):
        self._incidents = database.incidents

    async def create_once(
        self, idempotency_key: str, run_id: str, fields: dict
    ) -> tuple[str, bool]:
        new_incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
        result = await self._incidents.update_one(
            {"idempotency_key": idempotency_key},
            {
                "$setOnInsert": {
                    "_id": new_incident_id,
                    "run_id": run_id,
                    "created_at": datetime.now(UTC),
                    **fields,
                }
            },
            upsert=True,
        )
        if result.upserted_id is not None:
            return new_incident_id, True
        existing = await self._incidents.find_one({"idempotency_key": idempotency_key})
        return existing["_id"], False

    async def count(self) -> int:
        return await self._incidents.count_documents({})


def build_create_incident(incidents: IncidentRepository, injector: FailureInjector):
    async def create_incident(tool_input: CreateIncidentInput, context) -> dict:
        await injector.before_call("create_incident")
        idempotency_key = f"{context.run_id}:{context.tool_call_id}"
        incident_id, was_created = await incidents.create_once(
            idempotency_key,
            context.run_id,
            {
                "idempotency_key": idempotency_key,
                "title": tool_input.title,
                "description": tool_input.description,
                "severity": tool_input.severity.value,
            },
        )
        return injector.shape_output({"incident_id": incident_id, "created": was_created})

    return create_incident
