"""State schema for the report writer agent."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agents.common.models import Finding


class ReportState(BaseModel):
    """Shared state for the report writer agent."""

    scope: list[str] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    report: str | None = None
    finding_reports: dict[str, str] = Field(default_factory=dict)
    pdf_path: str | None = None
    error: str | None = None
    language: str = Field(
        default="auto",
        description=(
            "ISO 639-1 language code for the report (e.g. 'en', 'ru'). "
            "Use 'auto' to fall back to English."
        ),
    )
