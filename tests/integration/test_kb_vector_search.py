from pathlib import Path

from src.seed import seed_knowledge_base
from src.tools.knowledge_base import MongoKnowledgeBase
from tests.fakes import StubEmbeddings

KB_DIR = Path(__file__).resolve().parents[2] / "data" / "kb"
STUB_DIMENSIONS = 512


async def test_seeded_chunks_are_found_with_mongodb_vector_search(database):
    embedder = StubEmbeddings(STUB_DIMENSIONS)
    chunk_count = await seed_knowledge_base(database, embedder, KB_DIR, STUB_DIMENSIONS)

    hits = await MongoKnowledgeBase(database, embedder).search(
        "replica lag stale stock counts", limit=3
    )

    assert chunk_count >= 30
    assert hits[0]["doc_id"] == "inventory-service-runbook"
    assert hits[0]["score"] >= hits[-1]["score"]
