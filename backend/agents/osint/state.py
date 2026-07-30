"""State schema for the passive OSINT agent."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OSINTState(BaseModel):
    """Shared state for the passive OSINT agent."""

    target: str
    results: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
