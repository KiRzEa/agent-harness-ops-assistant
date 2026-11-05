import pytest

from src.core.config import Settings
from src.tools.executor import run_tool_with_guards
from src.tools.registry import ToolCallContext, ToolSpec
from src.tools.schemas import (
    SearchKnowledgeBaseInput,
    SearchKnowledgeBaseOutput,
    ToolError,
    TransientToolError,
)


class CallCounter:
    def __init__(self, failures):
        self.failures = list(failures)
        self.calls = 0

    async def __call__(self, tool_input, context):
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return {"results": []}


def make_spec(function) -> ToolSpec:
    return ToolSpec(
        "search_knowledge_base",
        "test",
        SearchKnowledgeBaseInput,
        SearchKnowledgeBaseOutput,
        function,
    )


async def run_guarded(function, max_retries=2, remaining_seconds=10):
    settings = Settings(_env_file=None, tool_max_retries=max_retries, tool_timeout_seconds=0.2)
    retries = []

    async def record_retry(attempt, code, message):
        retries.append(code)

    outcome = await run_tool_with_guards(
        make_spec(function),
        SearchKnowledgeBaseInput(query="x"),
        ToolCallContext("r", "c"),
        settings=settings,
        remaining_seconds=remaining_seconds,
        on_retry=record_retry,
    )
    return outcome, retries


async def test_transient_errors_are_retried_up_to_the_limit():
    counter = CallCounter([TransientToolError("flaky")] * 5)
    outcome, retries = await run_guarded(counter)
    assert not outcome.succeeded and outcome.attempts == 3 and counter.calls == 3
    assert retries == ["transient_error", "transient_error"]


async def test_permanent_errors_are_not_retried():
    counter = CallCounter([ToolError("bad", code="bad_input")])
    outcome, retries = await run_guarded(counter)
    assert outcome.error_code == "bad_input" and counter.calls == 1 and retries == []


async def test_unexpected_exception_becomes_an_error_outcome():
    outcome, _ = await run_guarded(CallCounter([ValueError("boom")]))
    assert outcome.error_code == "unexpected_error"


async def test_no_time_left_skips_the_call():
    counter = CallCounter([])
    outcome, _ = await run_guarded(counter, remaining_seconds=0)
    assert outcome.error_code == "time_limit" and counter.calls == 0


@pytest.mark.parametrize("retries_allowed,expected_calls", [(0, 1), (1, 2)])
async def test_retry_limit_is_configurable(retries_allowed, expected_calls):
    counter = CallCounter([TransientToolError("flaky")] * 5)
    await run_guarded(counter, max_retries=retries_allowed)
    assert counter.calls == expected_calls
