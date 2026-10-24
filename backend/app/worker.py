"""Background worker: runs queued jobs such as draft generation.

Run with `python -m app.worker`. Several workers can run at once on PostgreSQL.
"""

import logging
import time

from app.database import SessionLocal
from app.services import draft_service  # noqa: F401 — registers the draft job handler
from app.services import job_service

POLL_SECONDS = 1.0

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logger.info("Worker started")
    while True:
        with SessionLocal() as db:
            worked = job_service.process_next(db)
        if not worked:
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
