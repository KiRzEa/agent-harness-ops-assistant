import hashlib
import math
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from src.tools.knowledge_base import Embedder


class ScriptedChatModel(BaseChatModel):
    """Chat model that replays a fixed list of responses."""

    responses: list[Any] = Field(default_factory=list)
    repeat_last_response: bool = False
    received_messages: list[list[BaseMessage]] = Field(default_factory=list)
    call_delay_seconds: float = 0

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        self.received_messages.append(list(messages))
        if not self.responses:
            raise AssertionError("ScriptedChatModel has no responses left")
        next_response = self.responses[0] if self.repeat_last_response else self.responses.pop(0)
        if self.repeat_last_response and len(self.responses) > 1:
            self.responses.pop(0)
        if isinstance(next_response, Exception):
            raise next_response
        # Fresh copy so a repeated response does not reuse the message id the graph assigned.
        fresh_response = next_response.model_copy(update={"id": None})
        return ChatResult(generations=[ChatGeneration(message=fresh_response)])

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        if self.call_delay_seconds:
            import asyncio

            await asyncio.sleep(self.call_delay_seconds)
        return self._generate(messages, stop, run_manager, **kwargs)


def tool_call_message(name: str, args: dict, call_id: str = "call_1") -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


def many_tool_calls_message(calls: list[tuple[str, dict, str]]) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": args, "id": call_id} for name, args, call_id in calls],
    )


def text_message(text: str) -> AIMessage:
    return AIMessage(content=text)


class StubEmbeddings:
    """Deterministic fake embeddings based on word hashes."""

    def __init__(self, dimensions: int = 512):
        self.dimensions = dimensions

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for word in text.lower().split():
            digest = hashlib.sha256(word.encode()).digest()
            vector[digest[0] % self.dimensions] += 1.0
        length = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / length for value in vector]

    async def aembed_query(self, text: str) -> list[float]:
        return self._embed(text)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]


def cosine_similarity(first: list[float], second: list[float]) -> float:
    dot_product = sum(a * b for a, b in zip(first, second, strict=True))
    norm_product = math.sqrt(sum(a * a for a in first)) * math.sqrt(sum(b * b for b in second))
    return dot_product / norm_product if norm_product else 0.0


class InMemoryKnowledgeBase:
    def __init__(self, chunks: list[dict[str, Any]], embedder: Embedder):
        self._chunks = chunks
        self._embedder = embedder
        self._embeddings: list[list[float]] | None = None

    async def search(self, query: str, limit: int) -> list[dict[str, Any]]:
        if self._embeddings is None:
            self._embeddings = await self._embedder.aembed_documents(
                [chunk["text"] for chunk in self._chunks]
            )
        query_embedding = await self._embedder.aembed_query(query)
        scored = [
            {**chunk, "score": cosine_similarity(query_embedding, embedding)}
            for chunk, embedding in zip(self._chunks, self._embeddings, strict=True)
        ]
        return sorted(scored, key=lambda hit: hit["score"], reverse=True)[:limit]
