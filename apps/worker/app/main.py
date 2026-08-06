from __future__ import annotations

import os
import time

from apps.worker.app.tasks import redis_url as configured_redis_url


def main() -> None:
    redis_url = os.getenv("REDIS_URL", configured_redis_url)
    print(f"Worker shell configured with Redis broker: {redis_url}", flush=True)
    while True:
        time.sleep(30)


if __name__ == "__main__":
    main()
