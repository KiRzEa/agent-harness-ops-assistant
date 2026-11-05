from src.store.incidents import IncidentRepository
from src.tools.failure_injection import FailureInjector
from src.tools.schemas import CreateIncidentInput


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
