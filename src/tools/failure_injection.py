import asyncio
from collections import Counter
from typing import Any

from src.core.config import FailureMode
from src.tools.schemas import ToolError, TransientToolError


class FailureInjector:
    """Makes mock tools fail on purpose so retry and timeout paths can be exercised."""

    def __init__(self, mode: FailureMode = "none", fail_times: int = 1, slow_seconds: float = 30):
        self.mode = mode
        self.fail_times = fail_times
        self.slow_seconds = slow_seconds
        self._call_counts: Counter[str] = Counter()

    async def before_call(self, tool_name: str) -> None:
        self._call_counts[tool_name] += 1
        is_within_failing_calls = self._call_counts[tool_name] <= self.fail_times
        if self.mode == "transient" and is_within_failing_calls:
            raise TransientToolError("injected transient failure")
        if self.mode == "permanent":
            raise ToolError("injected permanent failure", code="injected_failure")
        if self.mode == "timeout" and is_within_failing_calls:
            await asyncio.sleep(self.slow_seconds)

    def shape_output(self, output: dict[str, Any]) -> dict[str, Any]:
        if self.mode == "invalid_output":
            return {"unexpected": "output does not match the schema"}
        return output
