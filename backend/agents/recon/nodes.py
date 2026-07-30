"""Reconnaissance agent node implementations."""

from __future__ import annotations

import logging
from typing import Any

from agents.common.models import ServiceInfo
from agents.recon.state import ReconState
from tools.recon.nmap import NmapTool

logger = logging.getLogger(__name__)


class ReconAgent:
    """Node callables for the reconnaissance agent."""

    def __init__(self, nmap_tool: NmapTool) -> None:
        """Create a recon agent."""
        self._nmap = nmap_tool

    def validate_scope(self, state: ReconState) -> dict[str, Any]:
        """Confirm the requested scope is non-empty and approved."""
        logger.info("Validating scope: %s", state.scope)
        if not state.scope:
            return {"error": "Empty scope: no targets provided", "approved": False}
        return {"approved": True}

    def scan(self, state: ReconState) -> dict[str, Any]:
        """Run reconnaissance against all approved targets."""
        if not state.approved:
            return {"error": "Scope validation failed; skipping reconnaissance"}

        open_ports: list[int] = []
        services: list[ServiceInfo] = []

        for target in state.scope:
            try:
                result = self._nmap.scan(target)
                open_ports.extend(result.open_ports)
                services.extend(ServiceInfo.model_validate(s) for s in result.services)
            except Exception as exc:
                logger.exception("Recon failed for %s", target)
                return {"error": f"Recon failed for {target}: {exc}"}

        logger.info(
            "Discovered %d open ports and %d services",
            len(open_ports),
            len(services),
        )
        return {"open_ports": open_ports, "services": services}
