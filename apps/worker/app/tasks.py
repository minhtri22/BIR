from __future__ import annotations

import os

import dramatiq
from dramatiq.brokers.redis import RedisBroker

redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
broker = RedisBroker(url=redis_url)
dramatiq.set_broker(broker)


@dramatiq.actor
def foundation_health_check() -> str:
    return "ok"

