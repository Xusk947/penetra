"""Report delivery adapters.

Reports are currently persisted to local disk only. This module is the single
extension point for shipping them to a remote destination (e.g. an object
store, ticketing system, or customer-facing API) once one is configured.
"""

from __future__ import annotations

import logging
from pathlib import Path

from agents.common.config import Settings

logger = logging.getLogger(__name__)


def deliver_report(pdf_path: Path, settings: Settings | None = None) -> str | None:
    """Deliver *pdf_path* to a remote endpoint if one is configured.

    Returns the delivery destination on success, or ``None`` if delivery is
    not configured (the report remains available locally).
    """
    settings = settings or Settings()
    endpoint = settings.report_remote_endpoint
    if not endpoint:
        logger.info(
            "No REPORT_REMOTE_ENDPOINT configured; report saved locally only at %s",
            pdf_path,
        )
        return None

    # Placeholder for a real remote upload (e.g. httpx.post(endpoint, files=...)).
    # Left unimplemented until a concrete delivery target is defined.
    logger.warning(
        "REPORT_REMOTE_ENDPOINT=%s is configured but remote delivery is not yet "
        "implemented; report remains local at %s",
        endpoint,
        pdf_path,
    )
    return None
