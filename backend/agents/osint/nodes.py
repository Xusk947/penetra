"""Passive OSINT agent node implementations."""

from __future__ import annotations

import logging
from typing import Any

from agents.common.config import Settings
from agents.osint.state import OSINTState
from tools.osint.base import OSINTResult
from tools.osint.tools import get_osint_tools

logger = logging.getLogger(__name__)


class OSINTAgent:
    """Node callables for passive OSINT collection."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Create the agent with configured OSINT tools."""
        self._settings = settings or Settings()
        self._tools = get_osint_tools(self._settings)

    def collect(self, state: OSINTState) -> dict[str, Any]:
        """Run all passive OSINT tools against the target."""
        logger.info("Collecting OSINT for %s", state.target)
        results: dict[str, OSINTResult] = {}
        for tool in self._tools:
            try:
                result = tool.run(state.target)
            except Exception as exc:
                result = OSINTResult(
                    source=tool.name,
                    target=state.target,
                    data={},
                    error=str(exc),
                )
            results[tool.name] = result
        return {"results": {name: r.model_dump() for name, r in results.items()}}
