import pytest
from pydantic import ValidationError

from src.tools.schemas import (
    CreateIncidentInput,
    GetServiceStatusInput,
    SearchKnowledgeBaseInput,
)


def test_incident_input_accepts_valid_values():
    incident = CreateIncidentInput(title=" Payments down ", description="500s", severity="high")
    assert incident.title == "Payments down"


@pytest.mark.parametrize(
    "bad_values",
    [
        {"title": "", "description": "x", "severity": "high"},
        {"title": "x", "description": "x", "severity": "urgent"},
        {"title": "x" * 201, "description": "x", "severity": "low"},
        {"title": "x", "description": "x", "severity": "low", "owner": "me"},
    ],
)
def test_incident_input_rejects_bad_values(bad_values):
    with pytest.raises(ValidationError):
        CreateIncidentInput(**bad_values)


def test_search_and_status_inputs_reject_empty():
    with pytest.raises(ValidationError):
        SearchKnowledgeBaseInput(query="  ")
    with pytest.raises(ValidationError):
        GetServiceStatusInput(service_name="")
