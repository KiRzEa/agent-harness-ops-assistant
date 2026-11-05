import httpx
import pytest

from src.main import create_app
from tests.fakes import ScriptedChatModel, text_message


@pytest.fixture
def api_client_factory(harness_factory):
    def make(chat_model):
        harness = harness_factory(chat_model)
        transport = httpx.ASGITransport(app=create_app(harness.service))
        return httpx.AsyncClient(transport=transport, base_url="http://test"), harness

    return make


async def test_start_run_and_read_it_back(api_client_factory):
    client, _ = api_client_factory(ScriptedChatModel(responses=[text_message("Hello.")]))
    async with client:
        started = await client.post("/runs", json={"objective": "Say hello"})
        assert started.status_code == 202
        run_id = started.json()["run_id"]
        assert started.json()["status"] == "COMPLETED"

        fetched = await client.get(f"/runs/{run_id}")
        assert fetched.json()["final_answer"] == "Hello."

        trace = await client.get(f"/runs/{run_id}/trace")
        assert trace.status_code == 200
        assert trace.json()[0]["type"] == "run_started"


@pytest.mark.parametrize(
    "body", [{"objective": ""}, {"objective": "   "}, {"objective": "x" * 2001}, {}]
)
async def test_invalid_objective_returns_422(api_client_factory, body):
    client, _ = api_client_factory(ScriptedChatModel())
    async with client:
        assert (await client.post("/runs", json=body)).status_code == 422


async def test_unknown_run_returns_404(api_client_factory):
    client, _ = api_client_factory(ScriptedChatModel())
    async with client:
        for method, path in [
            ("get", "/runs/nope"),
            ("get", "/runs/nope/trace"),
            ("post", "/runs/nope/approve"),
            ("post", "/runs/nope/reject"),
        ]:
            assert (await getattr(client, method)(path)).status_code == 404


async def test_approve_when_not_waiting_returns_409(api_client_factory):
    client, _ = api_client_factory(ScriptedChatModel(responses=[text_message("Hi")]))
    async with client:
        run_id = (await client.post("/runs", json={"objective": "Hi"})).json()["run_id"]
        assert (await client.post(f"/runs/{run_id}/approve")).status_code == 409


async def test_health_reports_ok(api_client_factory):
    client, _ = api_client_factory(ScriptedChatModel())
    async with client:
        response = await client.get("/health")
        assert response.status_code == 200 and response.json() == {"status": "ok"}
