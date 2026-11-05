from fastapi import APIRouter, HTTPException, Request, status

from src.api.schemas import EventResponse, RunResponse, StartRunRequest
from src.services.run_service import (
    ApprovalConflictError,
    InvalidObjectiveError,
    RunNotFoundError,
    RunService,
)

router = APIRouter()


def get_service(request: Request) -> RunService:
    return request.app.state.run_service


@router.post("/runs", response_model=RunResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_run(body: StartRunRequest, request: Request):
    try:
        return await get_service(request).start_run(body.objective)
    except InvalidObjectiveError as error:
        raise HTTPException(422, str(error)) from error


@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, request: Request):
    try:
        return await get_service(request).get_run(run_id)
    except RunNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found") from error


@router.get("/runs/{run_id}/trace", response_model=list[EventResponse])
async def get_trace(run_id: str, request: Request):
    try:
        return await get_service(request).get_trace(run_id)
    except RunNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found") from error


@router.post("/runs/{run_id}/approve", response_model=RunResponse)
async def approve_run(run_id: str, request: Request):
    return await decide(request, run_id, approve=True)


@router.post("/runs/{run_id}/reject", response_model=RunResponse)
async def reject_run(run_id: str, request: Request):
    return await decide(request, run_id, approve=False)


async def decide(request: Request, run_id: str, approve: bool):
    service = get_service(request)
    try:
        return await (service.approve(run_id) if approve else service.reject(run_id))
    except RunNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found") from error
    except ApprovalConflictError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error


@router.get("/health")
async def health(request: Request):
    await get_service(request).runs.ping()
    return {"status": "ok"}
