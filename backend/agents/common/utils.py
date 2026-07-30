"""Shared helpers for agents."""

from __future__ import annotations

from pathlib import Path


def load_system_prompt(agent_name: str) -> str:
    """Read the system prompt markdown file for an agent."""
    path = Path(__file__).parent.parent / agent_name / "system.md"
    return path.read_text(encoding="utf-8").strip()
