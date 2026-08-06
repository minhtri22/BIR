from __future__ import annotations

import os

import dramatiq
from dramatiq.brokers.redis import RedisBroker

from apps.api.app.analysis import process_analysis_job
from apps.api.app.config import Settings
from apps.api.app.database import make_engine, make_session_factory

redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
broker = RedisBroker(url=redis_url)
dramatiq.set_broker(broker)


@dramatiq.actor
def foundation_health_check() -> str:
    return "ok"


@dramatiq.actor
def run_static_analysis_job(job_id: str, request_id: str | None = None) -> str:
    settings = Settings()
    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)
    try:
        with session_factory() as db:
            process_analysis_job(db, settings, job_id=job_id, request_id=request_id)
    finally:
        engine.dispose()
    return "ok"
