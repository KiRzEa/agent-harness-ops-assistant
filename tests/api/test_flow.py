import httpx

from src.main import create_app
from tests.fakes import ScriptedChatModel, text_message, tool_call_message
from tests.integration.approval_helpers import INCIDENT_ARGS


def client_for(harness):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(harness.service)), base_url="http://test"
    )


async def test_start_wait_approve_complete(harness_factory):
    harness = harness_factory(
        ScriptedChatModel(
            responses=[
                tool_call_message("create_incident", INCIDENT_ARGS, "call_incident"),
                text_message("Incident opened."),
            ]
        )
    )
    async with client_for(harness) as client:
        started = (await client.post("/runs", json={"objective": "Open an incident"})).json()
        assert started["status"] == "AWAITING_APPROVAL"
        assert started["pending_approval"]["args"] == INCIDENT_ARGS

        finished = (await client.post(f"/runs/{started['run_id']}/approve")).json()
        assert finished["status"] == "COMPLETED"
        assert finished["final_answer"] == "Incident opened."
    assert await harness.incidents.count() == 1


async def test_start_wait_reject_complete(harness_factory):
    harness = harness_factory(
        ScriptedChatModel(
            responses=[
                tool_call_message("create_incident", INCIDENT_ARGS, "call_incident"),
                text_message("Skipped."),
            ]
        )
    )
    async with client_for(harness) as client:
        started = (await client.post("/runs", json={"objective": "Open an incident"})).json()
        finished = (await client.post(f"/runs/{started['run_id']}/reject")).json()
        assert finished["status"] == "COMPLETED"
        assert (await client.post(f"/runs/{started['run_id']}/reject")).status_code == 409
    assert await harness.incidents.count() == 0
