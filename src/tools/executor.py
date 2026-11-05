import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.core.config import Settings
from src.tools.registry import ToolCallContext, ToolSpec
from src.tools.schemas import ToolError, TransientToolError

RETRY_BACKOFF_BASE_SECONDS = 0.05
RETRY_BACKOFF_MAX_SECONDS = 1

RetryCallback = Callable[[int, str, str], Awaitable[None]]


@dataclass
class ToolOutcome:
    succeeded: bool
    attempts: int
    duration_ms: int
    output: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None


def describe_error(error: BaseException, attempt_timeout: float) -> tuple[str, str]:
    if isinstance(error, TimeoutError):
        return "timeout", f"Tool timed out after {attempt_timeout:.1f}s"
    if isinstance(error, ToolError):
        return error.code, str(error)
    return "unexpected_error", str(error)


async def run_tool_with_guards(
    spec: ToolSpec,
    tool_input: Any,
    context: ToolCallContext,
    *,
    settings: Settings,
    remaining_seconds: float,
    on_retry: RetryCallback,
) -> ToolOutcome:
    started_at = time.monotonic()
    attempts = 0
    attempt_timeout = settings.tool_timeout_seconds

    def elapsed_ms() -> int:
        return int((time.monotonic() - started_at) * 1000)

    async def attempt_call() -> dict[str, Any]:
        nonlocal attempts, attempt_timeout
        attempts += 1
        seconds_left = remaining_seconds - (time.monotonic() - started_at)
        if seconds_left <= 0:
            raise ToolError("Run time limit reached", code="time_limit")
        attempt_timeout = min(settings.tool_timeout_seconds, seconds_left)
        raw_output = await asyncio.wait_for(spec.function(tool_input, context), attempt_timeout)
        return spec.output_model.model_validate(raw_output).model_dump(mode="json")

    async def record_retry(retry_state: RetryCallState) -> None:
        code, message = describe_error(retry_state.outcome.exception(), attempt_timeout)
        await on_retry(retry_state.attempt_number, code, message)

    retrying = AsyncRetrying(
        stop=stop_after_attempt(settings.tool_max_retries + 1),
        wait=wait_exponential(multiplier=RETRY_BACKOFF_BASE_SECONDS, max=RETRY_BACKOFF_MAX_SECONDS),
        retry=retry_if_exception_type((TransientToolError, TimeoutError)),
        before_sleep=record_retry,
        reraise=True,
    )
    try:
        output = await retrying(attempt_call)
        return ToolOutcome(True, attempts, elapsed_ms(), output)
    except ValidationError as error:
        message = f"Tool output does not match its schema ({error.error_count()} error(s))"
        return ToolOutcome(False, attempts, elapsed_ms(), None, "invalid_output", message)
    except Exception as error:
        code, message = describe_error(error, attempt_timeout)
        return ToolOutcome(False, attempts, elapsed_ms(), None, code, message)
