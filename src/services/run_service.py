import uuid
from datetime import UTC, datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Command

from src.core.config import Settings
from src.core.enums import ApprovalStatus, EventType, RunStatus
from src.core.exceptions import (
    ApprovalConflictError,
    InvalidObjectiveError,
    RunNotFoundError,
)
from src.core.logging import bind_run_id, clear_run_id, get_logger
from src.graph.nodes import SYSTEM_PROMPT
from src.store.approvals import ApprovalRepository
from src.store.events import EventLog
from src.store.runs import RunRepository

logger = get_logger("service")

MAX_OBJECTIVE_LENGTH = 2000


class RunService:
    def __init__(
        self,
        *,
        graph,
        settings: Settings,
        runs: RunRepository,
        approvals: ApprovalRepository,
        events: EventLog,
    ):
        self.graph = graph
        self.settings = settings
        self.runs = runs
        self.approvals = approvals
        self.events = events

    def _graph_config(self, run_id: str) -> dict[str, Any]:
        steps_per_loop = 6
        return {
            "configurable": {"thread_id": run_id},
            "recursion_limit": self.settings.max_steps * steps_per_loop + 10,
        }

    async def start_run(self, objective: str) -> dict[str, Any]:
        cleaned_objective = objective.strip()
        if not cleaned_objective or len(cleaned_objective) > MAX_OBJECTIVE_LENGTH:
            raise InvalidObjectiveError(
                f"Objective must be between 1 and {MAX_OBJECTIVE_LENGTH} characters"
            )
        run_id = uuid.uuid4().hex
        await self.runs.create(run_id, cleaned_objective)
        await self.events.append(run_id, EventType.RUN_STARTED, {"objective": cleaned_objective})
        initial_state = {
            "run_id": run_id,
            "messages": [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=cleaned_objective),
            ],
            "step_count": 0,
            "active_seconds": 0.0,
            "repair_count": 0,
            "status": RunStatus.RUNNING.value,
            "final_answer": None,
            "error": None,
            "response_problem": None,
            "pending_read_calls": [],
            "pending_incident_call": None,
        }
        await self._drive(run_id, initial_state)
        return await self.get_run(run_id)

    async def get_run(self, run_id: str) -> dict[str, Any]:
        run = await self.runs.get(run_id)
        if run is None:
            raise RunNotFoundError(run_id)
        pending = None
        if run["status"] == RunStatus.AWAITING_APPROVAL.value:
            approval = await self.approvals.get_pending_for_run(run_id)
            if approval:
                pending = {"tool_name": approval["tool_name"], "args": approval["args"]}
        return {
            "run_id": run["_id"],
            "objective": run["objective"],
            "status": run["status"],
            "step_count": run["step_count"],
            "final_answer": run["final_answer"],
            "error": run["error"],
            "pending_approval": pending,
        }

    async def get_trace(self, run_id: str) -> list[dict[str, Any]]:
        if await self.runs.get(run_id) is None:
            raise RunNotFoundError(run_id)
        return await self.events.list_events(run_id)

    async def approve(self, run_id: str) -> dict[str, Any]:
        return await self._decide(run_id, ApprovalStatus.APPROVED)

    async def reject(self, run_id: str) -> dict[str, Any]:
        return await self._decide(run_id, ApprovalStatus.REJECTED)

    async def _decide(self, run_id: str, decision: ApprovalStatus) -> dict[str, Any]:
        if await self.runs.get(run_id) is None:
            raise RunNotFoundError(run_id)
        approval = await self.approvals.get_pending_for_run(run_id)
        if approval is None or not await self.approvals.decide(approval["_id"], decision):
            raise ApprovalConflictError("Run is not awaiting an approval decision")
        await self.events.append(
            run_id,
            EventType.APPROVAL_DECIDED,
            {"approval_id": approval["_id"], "decision": decision.value},
        )
        await self.runs.update(run_id, status=RunStatus.RUNNING.value)
        await self._drive(run_id, Command(resume=decision.value))
        return await self.get_run(run_id)

    async def _drive(self, run_id: str, graph_input: Any) -> None:
        config = self._graph_config(run_id)
        bind_run_id(run_id)
        try:
            await self.graph.ainvoke(graph_input, config)
            snapshot = await self.graph.aget_state(config)
        except Exception as error:
            logger.exception("run_crashed", run_id=run_id)
            await self._finish_run(
                run_id,
                RunStatus.FAILED.value,
                None,
                {"code": "internal_error", "message": str(error)},
                None,
            )
            return
        finally:
            clear_run_id()

        state = snapshot.values
        if snapshot.next:
            await self.runs.update(
                run_id, status=RunStatus.AWAITING_APPROVAL.value, step_count=state["step_count"]
            )
            return
        await self._finish_run(
            run_id, state["status"], state["final_answer"], state["error"], state["step_count"]
        )

    async def _finish_run(
        self,
        run_id: str,
        status: str,
        final_answer: str | None,
        error: dict | None,
        step_count: int | None,
    ) -> None:
        fields: dict[str, Any] = {
            "status": status,
            "final_answer": final_answer,
            "error": error,
            "finished_at": datetime.now(UTC),
        }
        if step_count is not None:
            fields["step_count"] = step_count
        await self.runs.update(run_id, **fields)
        await self.events.append(run_id, EventType.RUN_FINISHED, {"status": status})
