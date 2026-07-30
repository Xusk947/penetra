"""Pentest orchestrator entry point."""

from __future__ import annotations

from agents.common.config import Settings
from agents.orchestrator.graph import build_graph

_settings = Settings()
graph = build_graph(_settings)
