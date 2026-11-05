import re
from pathlib import Path
from typing import Any, Protocol

from pymongo.asynchronous.database import AsyncDatabase

from src.tools.failure_injection import FailureInjector
from src.tools.schemas import SearchKnowledgeBaseInput, ToolError

VECTOR_INDEX_NAME = "kb_vector_index"
SNIPPET_MAX_CHARS = 400


class Embedder(Protocol):
    async def aembed_query(self, text: str) -> list[float]: ...

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]: ...


class KnowledgeBase(Protocol):
    async def search(self, query: str, limit: int) -> list[dict[str, Any]]: ...


def load_knowledge_chunks(documents_dir: Path) -> list[dict[str, Any]]:
    """Split each markdown file into one chunk per `##` section."""
    chunks = []
    for document_path in sorted(documents_dir.glob("*.md")):
        text = document_path.read_text()
        title_match = re.search(r"^# (.+)$", text, flags=re.MULTILINE)
        title = title_match.group(1).strip() if title_match else document_path.stem
        tags_match = re.search(r"^Tags: (.+)$", text, flags=re.MULTILINE)
        tags = [tag.strip() for tag in tags_match.group(1).split(",")] if tags_match else []
        sections = re.split(r"^## ", text, flags=re.MULTILINE)[1:]
        for index, section in enumerate(sections):
            heading, _, body = section.partition("\n")
            chunks.append(
                {
                    "_id": f"{document_path.stem}#{index}",
                    "doc_id": document_path.stem,
                    "title": title,
                    "text": f"{title} - {heading.strip()}\n{body.strip()}",
                    "tags": tags,
                }
            )
    return chunks


class MongoKnowledgeBase:
    def __init__(self, database: AsyncDatabase, embedder: Embedder):
        self._chunks = database.kb_chunks
        self._embedder = embedder

    async def search(self, query: str, limit: int) -> list[dict[str, Any]]:
        query_embedding = await self._embedder.aembed_query(query)
        pipeline = [
            {
                "$vectorSearch": {
                    "index": VECTOR_INDEX_NAME,
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": max(limit * 10, 50),
                    "limit": limit,
                }
            },
            {"$project": {"embedding": 0, "score": {"$meta": "vectorSearchScore"}}},
        ]
        cursor = await self._chunks.aggregate(pipeline)
        return await cursor.to_list(length=limit)


def build_search_knowledge_base(
    knowledge_base: KnowledgeBase, injector: FailureInjector, result_limit: int = 4
):
    async def search_knowledge_base(tool_input: SearchKnowledgeBaseInput, context) -> dict:
        await injector.before_call("search_knowledge_base")
        try:
            hits = await knowledge_base.search(tool_input.query, result_limit)
        except Exception as error:
            raise ToolError(
                f"Knowledge base search failed: {error}", code="search_failed"
            ) from error
        results = [
            {
                "doc_id": hit["doc_id"],
                "title": hit["title"],
                "snippet": hit["text"][:SNIPPET_MAX_CHARS],
                "score": float(hit["score"]),
            }
            for hit in hits
        ]
        return injector.shape_output({"results": results})

    return search_knowledge_base
