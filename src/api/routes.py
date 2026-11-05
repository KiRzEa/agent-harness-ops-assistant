from fastapi import APIRouter, HTTPException, status

from src.api.dependencies import RunServiceDep
from src.api.schemas import EventResponse, RunResponse, StartRunRequest
from src.core.exceptions import (
    ApprovalConflictError,
    InvalidObjectiveError,
    RunNotFoundError,
)
from src.services.run_service import RunService

router = APIRouter()


@router.post("/runs", response_model=RunResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_run(body: StartRunRequest, service: RunServiceDep):
    try:
        return await service.start_run(body.objective)
    except InvalidObjectiveError as error:
        raise HTTPException(422, str(error)) from error


@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, service: RunServiceDep):
    try:
        return await service.get_run(run_id)
    except RunNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found") from error


@router.get("/runs/{run_id}/trace", response_model=list[EventResponse])
async def get_trace(run_id: str, service: RunServiceDep):
    try:
        return await service.get_trace(run_id)
    except RunNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found") from error


@router.post("/runs/{run_id}/approve", response_model=RunResponse)
async def approve_run(run_id: str, service: RunServiceDep):
    return await decide(service, run_id, approve=True)


@router.post("/runs/{run_id}/reject", response_model=RunResponse)
async def reject_run(run_id: str, service: RunServiceDep):
    return await decide(service, run_id, approve=False)


async def decide(service: RunService, run_id: str, approve: bool):
    try:
        return await (service.approve(run_id) if approve else service.reject(run_id))
    except RunNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found") from error
    except ApprovalConflictError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error


@router.get("/health")
async def health(service: RunServiceDep):
    await service.runs.ping()
    return {"status": "ok"}
