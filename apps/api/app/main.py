from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from apps.api.app.bootstrap import seed_development_user
from apps.api.app.config import Settings
from apps.api.app.database import Base, make_engine, make_session_factory
from apps.api.app.routers import artifacts, auth, health, projects, review_stub


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)
    app.state.engine = engine
    app.state.SessionLocal = session_factory
    app.state.session_idle_delta = timedelta(seconds=settings.session_idle_seconds)

    if settings.auto_create_db:
        Base.metadata.create_all(bind=engine)

    with session_factory() as db:
        seed_development_user(db, settings)

    yield
    engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings()
    app = FastAPI(title="Business Forensics Platform API", version="0.1.0", lifespan=lifespan)
    app.state.settings = resolved_settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token", "X-Request-ID"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(projects.router, prefix="/api/v1")
    app.include_router(artifacts.router, prefix="/api/v1")
    app.include_router(review_stub.router, prefix="/api/v1")
    return app


app = create_app()
