"""State schema for the vulnerability analysis agent."""

from __future__ import annotations

import operator
from typing import Annotated

from pydantic import BaseModel, Field

from agents.common.models import Finding, ServiceInfo


class VulnState(BaseModel):
    """Shared state for the vulnerability analysis agent."""

    services: list[ServiceInfo] = Field(default_factory=list)
    findings: Annotated[list[Finding], operator.add] = Field(default_factory=list)
    error: str | None = None
