from typing import Annotated

from fastapi import Depends, Request

from src.services.run_service import RunService


def get_run_service(request: Request) -> RunService:
    return request.app.state.run_service


RunServiceDep = Annotated[RunService, Depends(get_run_service)]
