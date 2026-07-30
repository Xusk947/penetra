"""Shared Pydantic models across agents."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


def _new_finding_id() -> str:
    """Generate a short, human-friendly unique identifier for a finding."""
    return f"VULN-{uuid.uuid4().hex[:8].upper()}"


class ServiceInfo(BaseModel):
    """Service fingerprint discovered on a target."""

    port: int
    protocol: str
    service: str
    version: str | None = None


class Finding(BaseModel):
    """Security finding produced by the vulnerability analysis agent.

    ``id`` uniquely identifies the finding so it can be traced, cross-referenced
    and reported on individually. ``agent`` and ``tool`` record which domain
    agent (client/server/iot) and which specific check discovered it, so the
    full chain of custody from scan to finding can be audited.
    """

    id: str = Field(default_factory=_new_finding_id)
    title: str
    severity: str
    confidence: str
    description: str
    cwe: str | None = None
    remediation: str | None = None
    category: str | None = None
    score: int | None = Field(None, ge=1, le=5)
    steps: list[str] = Field(default_factory=list)
    agent: str | None = None
    tool: str | None = None
