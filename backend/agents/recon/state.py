"""State schema for the reconnaissance agent."""

from __future__ import annotations

import operator
from typing import Annotated

from pydantic import BaseModel, Field

from agents.common.models import ServiceInfo


class ReconState(BaseModel):
    """Shared state for the reconnaissance agent."""

    scope: list[str] = Field(default_factory=list)
    approved: bool = False
    open_ports: Annotated[list[int], operator.add] = Field(default_factory=list)
    services: Annotated[list[ServiceInfo], operator.add] = Field(default_factory=list)
    error: str | None = None
