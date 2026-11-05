from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ToolError(Exception):
    def __init__(self, message: str, code: str = "tool_error"):
        super().__init__(message)
        self.code = code


class TransientToolError(ToolError):
    def __init__(self, message: str, code: str = "transient_error"):
        super().__init__(message, code)


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ServiceHealth(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SearchKnowledgeBaseInput(StrictModel):
    query: str = Field(min_length=1, max_length=500)


class KnowledgeBaseHit(StrictModel):
    doc_id: str
    title: str
    snippet: str
    score: float


class SearchKnowledgeBaseOutput(StrictModel):
    results: list[KnowledgeBaseHit]


class GetServiceStatusInput(StrictModel):
    service_name: str = Field(min_length=1, max_length=100)


class GetServiceStatusOutput(StrictModel):
    service_name: str
    status: ServiceHealth
    updated_at: str
    summary: str


class CreateIncidentInput(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=4000)
    severity: Severity


class CreateIncidentOutput(StrictModel):
    incident_id: str
    created: bool
