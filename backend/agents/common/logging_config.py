"""Run-scoped logging so every pentest run is recorded to disk as it happens."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_run_logging(logs_dir: str = "reports/logs") -> Path:
    """Attach a dedicated file handler for one pentest run and return its path.

    Every call creates a new timestamped log file and attaches a handler to
    the root logger for the duration of the process. This lets the full
    trace of every agent/tool action be reviewed after the fact, in parallel
    with (not instead of) the live console output.
    """
    Path(logs_dir).mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = Path(logs_dir) / f"run_{stamp}_{uuid.uuid4().hex[:6]}.log"

    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))

    root = logging.getLogger()
    if root.level > logging.INFO or root.level == logging.NOTSET:
        root.setLevel(logging.INFO)
    root.addHandler(handler)

    logging.getLogger(__name__).info("Run log started: %s", log_path)
    return log_path
