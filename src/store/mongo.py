from pymongo import ASCENDING, DESCENDING, AsyncMongoClient, MongoClient
from pymongo.asynchronous.database import AsyncDatabase

from src.core.config import Settings


def create_mongo_client(settings: Settings) -> AsyncMongoClient:
    return AsyncMongoClient(settings.mongodb_uri, tz_aware=True)


async def create_indexes(database: AsyncDatabase) -> None:
    await database.runs.create_index([("status", ASCENDING), ("created_at", DESCENDING)])
    await database.events.create_index([("run_id", ASCENDING), ("seq", ASCENDING)], unique=True)
    await database.approvals.create_index(
        [("run_id", ASCENDING), ("tool_call_id", ASCENDING)], unique=True
    )
    await database.incidents.create_index("idempotency_key", unique=True)


def create_sync_mongo_client(settings: Settings) -> MongoClient:
    # The LangGraph Mongo checkpointer only accepts a synchronous client.
    return MongoClient(settings.mongodb_uri, tz_aware=True)
