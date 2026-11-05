from pathlib import Path

import pytest

from src.tools.failure_injection import FailureInjector
from src.tools.knowledge_base import (
    build_search_knowledge_base,
    load_knowledge_chunks,
)
from src.tools.registry import ToolCallContext
from src.tools.schemas import GetServiceStatusInput, SearchKnowledgeBaseInput, ToolError
from src.tools.service_status import build_get_service_status
from tests.fakes import InMemoryKnowledgeBase, StubEmbeddings

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
CONTEXT = ToolCallContext(run_id="run-1", tool_call_id="call-1")


async def test_service_status_returns_known_service():
    get_status = build_get_service_status(DATA_DIR / "services.json", FailureInjector())
    result = await get_status(GetServiceStatusInput(service_name="Payments-API"), CONTEXT)
    assert result["service_name"] == "payments-api"
    assert result["status"] == "degraded"


async def test_service_status_unknown_service_is_a_permanent_error():
    get_status = build_get_service_status(DATA_DIR / "services.json", FailureInjector())
    with pytest.raises(ToolError) as error_info:
        await get_status(GetServiceStatusInput(service_name="billing"), CONTEXT)
    assert error_info.value.code == "service_not_found"


def test_knowledge_chunks_cover_all_documents():
    chunks = load_knowledge_chunks(DATA_DIR / "kb")
    assert len({chunk["doc_id"] for chunk in chunks}) >= 15
    assert all(chunk["text"] and chunk["title"] for chunk in chunks)


async def test_knowledge_base_search_finds_relevant_chunk():
    knowledge_base = InMemoryKnowledgeBase(load_knowledge_chunks(DATA_DIR / "kb"), StubEmbeddings())
    search = build_search_knowledge_base(knowledge_base, FailureInjector())
    result = await search(SearchKnowledgeBaseInput(query="replica lag stale stock counts"), CONTEXT)
    assert result["results"][0]["doc_id"] == "inventory-service-runbook"
