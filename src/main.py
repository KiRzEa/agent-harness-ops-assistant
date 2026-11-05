from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes import router
from src.bootstrap import create_run_service
from src.core.config import get_settings
from src.core.logging import configure_logging
from src.services.run_service import RunService


def create_app(run_service: RunService | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if run_service is not None:
            app.state.run_service = run_service
            yield
            return
        configure_logging()
        async with create_run_service(get_settings()) as service:
            app.state.run_service = service
            yield

    app = FastAPI(title="Ops Assistant Agent Harness", lifespan=lifespan)
    app.include_router(router)
    if run_service is not None:
        app.state.run_service = run_service
    return app


app = create_app()
