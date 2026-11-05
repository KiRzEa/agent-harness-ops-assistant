import json
from pathlib import Path

from src.tools.failure_injection import FailureInjector
from src.tools.schemas import GetServiceStatusInput, ToolError


def load_services(services_path: Path) -> dict[str, dict]:
    services = json.loads(services_path.read_text())
    return {service["name"].lower(): service for service in services}


def build_get_service_status(services_path: Path, injector: FailureInjector):
    services_by_name = load_services(services_path)

    async def get_service_status(tool_input: GetServiceStatusInput, context) -> dict:
        await injector.before_call("get_service_status")
        service = services_by_name.get(tool_input.service_name.lower())
        if service is None:
            known_names = ", ".join(sorted(services_by_name))
            raise ToolError(
                f"Unknown service '{tool_input.service_name}'. Known services: {known_names}",
                code="service_not_found",
            )
        return injector.shape_output(
            {
                "service_name": service["name"],
                "status": service["status"],
                "updated_at": service["updated_at"],
                "summary": service["summary"],
            }
        )

    return get_service_status
