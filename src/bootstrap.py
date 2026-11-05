from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from langgraph.checkpoint.mongodb import MongoDBSaver

from src.ai_models.chat_model import build_chat_model
from src.ai_models.embeddings import build_embeddings
from src.core.config import Settings
from src.graph.builder import build_graph
from src.graph.dependencies import GraphDependencies
from src.services.run_service import RunService
from src.store.approvals import ApprovalRepository
from src.store.events import EventLog
from src.store.incidents import IncidentRepository
from src.store.mongo import create_indexes, create_mongo_client, create_sync_mongo_client
from src.store.runs import RunRepository
from src.tools.failure_injection import FailureInjector
from src.tools.knowledge_base import MongoKnowledgeBase
from src.tools.registry import build_tool_registry

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@asynccontextmanager
async def create_run_service(settings: Settings) -> AsyncGenerator[RunService]:
    async_client = create_mongo_client(settings)
    sync_client = create_sync_mongo_client(settings)
    try:
        database = async_client[settings.mongodb_db]
        await create_indexes(database)
        events = EventLog(database)
        approvals = ApprovalRepository(database)
        tools = build_tool_registry(
            knowledge_base=MongoKnowledgeBase(database, build_embeddings(settings)),
            incidents=IncidentRepository(database),
            services_path=DATA_DIR / "services.json",
            injector=FailureInjector(settings.failure_mode),
        )
        graph = build_graph(
            GraphDependencies(
                settings=settings,
                chat_model=build_chat_model(settings),
                tools=tools,
                events=events,
                approvals=approvals,
            ),
            MongoDBSaver(sync_client, db_name=settings.mongodb_db),
        )
        yield RunService(
            graph=graph,
            settings=settings,
            runs=RunRepository(database),
            approvals=approvals,
            events=events,
        )
    finally:
        sync_client.close()
        await async_client.close()
