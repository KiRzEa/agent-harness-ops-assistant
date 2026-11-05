from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class StartRunRequest(BaseModel):
    objective: str = Field(min_length=1, max_length=2000)


class PendingApproval(BaseModel):
    tool_name: str
    args: dict[str, Any]


class RunResponse(BaseModel):
    run_id: str
    objective: str
    status: str
    step_count: int
    final_answer: str | None
    error: dict[str, str] | None
    pending_approval: PendingApproval | None


class EventResponse(BaseModel):
    seq: int
    type: str
    ts: datetime
    duration_ms: int | None
    payload: dict[str, Any]
