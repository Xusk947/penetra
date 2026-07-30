"""State schema for the research agent."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ResearchState(BaseModel):
    """Shared state for the research browser agent."""

    target: str = ""
    page_title: str | None = None
    page_text: str = ""
    links: list[str] = Field(default_factory=list)
    summary: str | None = None
    error: str | None = None
