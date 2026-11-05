import uuid

import pytest
from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError

from src.core.config import Settings
from src.store.mongo import create_indexes

MONGODB_URI = "mongodb://localhost:27017/?directConnection=true"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        openai_api_key="test-key",
        mongodb_uri=MONGODB_URI,
        mongodb_db=f"test_{uuid.uuid4().hex[:10]}",
        max_steps=6,
        max_run_seconds=10,
        tool_timeout_seconds=0.3,
        tool_max_retries=2,
        max_repairs=2,
    )


@pytest.fixture
async def database(settings):
    client = AsyncMongoClient(MONGODB_URI, tz_aware=True, serverSelectionTimeoutMS=1500)
    try:
        await client.admin.command("ping")
    except PyMongoError:
        await client.close()
        pytest.skip("MongoDB is not running; start it with `docker compose up -d`")
    test_database = client[settings.mongodb_db]
    await create_indexes(test_database)
    yield test_database
    await client.drop_database(settings.mongodb_db)
    await client.close()


@pytest.fixture
def harness_factory(settings, database):
    from dataclasses import dataclass
    from pathlib import Path

    from langgraph.checkpoint.mongodb import MongoDBSaver
    from pymongo import MongoClient

    from src.graph.builder import build_graph
    from src.graph.dependencies import GraphDependencies
    from src.services.run_service import RunService
    from src.store.events import EventLog
    from src.store.runs import ApprovalRepository, RunRepository
    from src.tools.failure_injection import FailureInjector
    from src.tools.incidents import IncidentRepository
    from src.tools.knowledge_base import load_knowledge_chunks
    from src.tools.registry import build_tool_registry
    from tests.fakes import InMemoryKnowledgeBase, StubEmbeddings

    data_dir = Path(__file__).resolve().parent.parent / "data"
    sync_clients = []

    @dataclass
    class Harness:
        service: RunService
        incidents: IncidentRepository
        events: EventLog
        approvals: ApprovalRepository
        injector: FailureInjector
        settings: object

    def make(chat_model, injector=None, settings_override=None):
        active_settings = settings_override or settings
        injector = injector or FailureInjector()
        events = EventLog(database)
        approvals = ApprovalRepository(database)
        incidents = IncidentRepository(database)
        knowledge_base = InMemoryKnowledgeBase(
            load_knowledge_chunks(data_dir / "kb"), StubEmbeddings()
        )
        tools = build_tool_registry(
            knowledge_base=knowledge_base,
            incidents=incidents,
            services_path=data_dir / "services.json",
            injector=injector,
        )
        sync_client = MongoClient(MONGODB_URI, tz_aware=True)
        sync_clients.append(sync_client)
        graph = build_graph(
            GraphDependencies(
                settings=active_settings,
                chat_model=chat_model,
                tools=tools,
                events=events,
                approvals=approvals,
            ),
            MongoDBSaver(sync_client, db_name=active_settings.mongodb_db),
        )
        service = RunService(
            graph=graph,
            settings=active_settings,
            runs=RunRepository(database),
            approvals=approvals,
            events=events,
        )
        return Harness(service, incidents, events, approvals, injector, active_settings)

    yield make
    for sync_client in sync_clients:
        sync_client.close()
