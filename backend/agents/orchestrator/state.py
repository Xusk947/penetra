"""State schema for the pentest orchestrator agent."""

from __future__ import annotations

import operator
from typing import Annotated, Any

from pydantic import BaseModel, Field

from agents.common.models import Finding


class OrchestratorState(BaseModel):
    """Shared state for the pentest orchestrator."""

    scope: list[str] = Field(default_factory=list)
    approved: bool = False
    findings: Annotated[list[Finding], operator.add] = Field(default_factory=list)
    report: str | None = None
    finding_reports: dict[str, str] = Field(default_factory=dict)
    pdf_path: str | None = None
    error: str | None = None
    metadata: Annotated[dict[str, Any], operator.or_] = Field(default_factory=dict)
    language: str = Field(
        default="auto",
        description=(
            "ISO 639-1 language code for the report (e.g. 'en', 'ru'). "
            "Use 'auto' to fall back to English."
        ),
    )
    focus: str = Field(
        default="all",
        description=(
            "Intent/focus hint for the pentest. Keywords like 'backend', 'server', "
            "'client', 'web', 'iot', 'credentials', 'access' can be used to run "
            "only the relevant domain agents. 'all' runs everything."
        ),
    )
