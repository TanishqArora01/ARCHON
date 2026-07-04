from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import update

from src.api.agents import router as agents_router
from src.api.analysis import router as analysis_router
from src.api.auth import router as auth_router
from src.api.graph import router as graph_router
from src.api.oauth import router as oauth_router
from src.api.repositories import router as repositories_router
from src.api.webhooks import router as webhooks_router
from src.api.security import require_api_token
from src.core.config import settings
from src.db.models import AnalysisJob
from src.db.session import AsyncSessionLocal, create_database_schema, dispose_database_engine
from src.observability.telemetry import init_production_telemetry


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_production_telemetry()
    if settings.ENVIRONMENT in {"development", "test"}:
        try:
            await create_database_schema()
        except Exception:
            app.state.database_bootstrap_failed = True
    # Clean up stale 'queued' jobs from previous server instances
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(AnalysisJob)
                .where(AnalysisJob.status == "queued", AnalysisJob.attempts == 0)
                .values(status="failed", last_error="Server restarted — job never processed")
            )
            await session.commit()
    except Exception:
        pass  # Non-fatal — don't block startup
    yield
    await dispose_database_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title=f"{settings.APP_NAME} API",
        version=settings.APP_VERSION,
        description="Repository intelligence and AI Staff Engineer API.",
        lifespan=lifespan,
    )
    @app.get("/")
    async def root():
        return {"status": "ok", "service": settings.APP_NAME}
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(agents_router)
    app.include_router(analysis_router)
    app.include_router(auth_router)
    app.include_router(oauth_router)
    app.include_router(repositories_router)
    app.include_router(webhooks_router)
    app.include_router(graph_router)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": settings.APP_NAME}

    @app.get("/api/v1/version", dependencies=[Depends(require_api_token)])
    async def version() -> dict[str, str]:
        return {"name": settings.APP_NAME, "version": settings.APP_VERSION}

    return app


app = create_app()
