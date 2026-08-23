"""Application logging.

uvicorn configures only its own loggers, so without this every logger.info() in
app code is discarded — including the webhook and backfill lines that say whether
background work actually happened.
"""

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(levelname)s:    %(name)s - %(message)s"))

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

    # Keep uvicorn's access log, but let it use our handler instead of duplicating.
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True

    # httpx logs every outbound request at INFO — useful for Strava calls, noise everywhere else.
    logging.getLogger("httpx").setLevel(logging.WARNING)
