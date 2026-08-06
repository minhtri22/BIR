from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.app.dependencies import get_db
from apps.api.app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    db.execute(text("select 1"))
    return HealthResponse(status="ok", database="ok")


@router.get("/worker/health", response_model=HealthResponse)
def worker_health(db: Session = Depends(get_db)) -> HealthResponse:
    db.execute(text("select 1"))
    return HealthResponse(status="ok", database="ok", worker="shell-configured")

