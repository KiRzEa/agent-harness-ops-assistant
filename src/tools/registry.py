from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from src.store.incidents import IncidentRepository
from src.tools.failure_injection import FailureInjector
from src.tools.incidents import build_create_incident
from src.tools.knowledge_base import KnowledgeBase, build_search_knowledge_base
from src.tools.schemas import (
    CreateIncidentInput,
    CreateIncidentOutput,
    GetServiceStatusInput,
    GetServiceStatusOutput,
    SearchKnowledgeBaseInput,
    SearchKnowledgeBaseOutput,
)
from src.tools.service_status import build_get_service_status


@dataclass(frozen=True)
class ToolCallContext:
    run_id: str
    tool_call_id: str


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    function: Callable[[Any, ToolCallContext], Awaitable[dict]]
    is_side_effecting: bool = False

    def as_openai_tool(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_model.model_json_schema(),
            },
        }


def build_tool_registry(
    *,
    knowledge_base: KnowledgeBase,
    incidents: IncidentRepository,
    services_path: Path,
    injector: FailureInjector,
) -> dict[str, ToolSpec]:
    specs = [
        ToolSpec(
            name="search_knowledge_base",
            description="Search internal runbooks and policies for how-to and escalation guidance.",
            input_model=SearchKnowledgeBaseInput,
            output_model=SearchKnowledgeBaseOutput,
            function=build_search_knowledge_base(knowledge_base, injector),
        ),
        ToolSpec(
            name="get_service_status",
            description="Get the current health status of a named service.",
            input_model=GetServiceStatusInput,
            output_model=GetServiceStatusOutput,
            function=build_get_service_status(services_path, injector),
        ),
        ToolSpec(
            name="create_incident",
            description=(
                "Create an incident in the external incident system. Requires operator approval; "
                "only call it when an incident is clearly warranted."
            ),
            input_model=CreateIncidentInput,
            output_model=CreateIncidentOutput,
            function=build_create_incident(incidents, injector),
            is_side_effecting=True,
        ),
    ]
    return {spec.name: spec for spec in specs}
