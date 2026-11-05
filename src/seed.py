import asyncio
from pathlib import Path

from pymongo import AsyncMongoClient
from pymongo.operations import SearchIndexModel

from src.ai_models.embeddings import build_embeddings
from src.core.config import get_settings
from src.tools.knowledge_base import VECTOR_INDEX_NAME, load_knowledge_chunks

ROOT = Path(__file__).resolve().parent.parent

EMBEDDING_DIMENSIONS = 1536
INDEX_READY_TIMEOUT_SECONDS = 120


async def wait_until_index_is_queryable(collection) -> None:
    for _ in range(INDEX_READY_TIMEOUT_SECONDS):
        indexes = await (await collection.list_search_indexes(VECTOR_INDEX_NAME)).to_list(length=1)
        if indexes and indexes[0].get("queryable"):
            return
        await asyncio.sleep(1)
    raise TimeoutError("Vector index did not become queryable in time")


async def seed_knowledge_base(database, embedder, documents_dir: Path, dimensions: int) -> int:
    chunks = load_knowledge_chunks(documents_dir)
    embeddings = await embedder.aembed_documents([chunk["text"] for chunk in chunks])
    collection = database.kb_chunks
    await collection.delete_many({})
    await collection.insert_many(
        [
            {**chunk, "embedding": embedding}
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]
    )
    existing = await (await collection.list_search_indexes(VECTOR_INDEX_NAME)).to_list(length=1)
    if not existing:
        await collection.create_search_index(
            SearchIndexModel(
                name=VECTOR_INDEX_NAME,
                type="vectorSearch",
                definition={
                    "fields": [
                        {
                            "type": "vector",
                            "path": "embedding",
                            "numDimensions": dimensions,
                            "similarity": "cosine",
                        },
                        {"type": "filter", "path": "tags"},
                    ]
                },
            )
        )
    await wait_until_index_is_queryable(collection)
    return len(chunks)


async def main() -> None:
    settings = get_settings()
    client = AsyncMongoClient(settings.mongodb_uri)
    count = await seed_knowledge_base(
        client[settings.mongodb_db],
        build_embeddings(settings),
        ROOT / "data" / "kb",
        EMBEDDING_DIMENSIONS,
    )
    print(f"Seeded {count} knowledge base chunks into '{settings.mongodb_db}'")
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
