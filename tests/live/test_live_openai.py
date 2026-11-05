import uuid

import pytest
from pymongo import AsyncMongoClient

from src.bootstrap import create_run_service
from src.core.config import Settings

pytestmark = pytest.mark.live


async def test_real_model_checks_a_service_and_answers():
    settings = Settings(mongodb_db=f"live_{uuid.uuid4().hex[:8]}")
    if not settings.openai_api_key.get_secret_value():
        pytest.skip("OPENAI_API_KEY is not set")
    try:
        async with create_run_service(settings) as service:
            run = await service.start_run("What is the current status of auth-service?")
        assert run["status"] == "COMPLETED"
        assert "healthy" in run["final_answer"].lower()
    finally:
        client = AsyncMongoClient(settings.mongodb_uri)
        await client.drop_database(settings.mongodb_db)
        await client.close()
