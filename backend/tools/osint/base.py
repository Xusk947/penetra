"""Base class for passive OSINT tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from agents.common.config import Settings


class OSINTResult(BaseModel):
    """Result returned by an OSINT tool."""

    source: str
    target: str
    data: dict[str, Any]
    error: str | None = None


class BaseOSINTTool(ABC):
    """Abstract passive OSINT tool.

    Subclasses implement ``_run`` for live lookups and ``_mock_result`` for
    deterministic test output. When ``Settings.osint_mock`` is ``True`` the
    mock path is used.
    """

    name: str = "base"
    required_settings: tuple[str, ...] = ()

    def __init__(self, settings: Settings | None = None) -> None:
        """Create the tool with optional runtime settings."""
        self._settings = settings or Settings()

    def is_configured(self) -> bool:
        """Return True if the tool can run in the current environment."""
        if self._settings.osint_mock or not self.required_settings:
            return True
        return all(getattr(self._settings, key) for key in self.required_settings)

    def configuration_status(self) -> str:
        """Return a short human-readable status for the current environment."""
        if self._settings.osint_mock:
            return "available (mock mode)"
        if not self.required_settings:
            return "available"
        missing = [key for key in self.required_settings if not getattr(self._settings, key)]
        if not missing:
            return "configured"
        return f"missing: {', '.join(missing)}"

    def run(self, target: str) -> OSINTResult:
        """Execute the tool against *target* and return a result."""
        if self._settings.osint_mock:
            return self._mock_result(target)
        try:
            return self._run(target)
        except Exception as exc:
            return OSINTResult(
                source=self.name, target=target, data={}, error=str(exc)
            )

    @abstractmethod
    def _run(self, target: str) -> OSINTResult:
        """Perform a live lookup."""

    @abstractmethod
    def _mock_result(self, target: str) -> OSINTResult:
        """Return deterministic mock data for tests."""
