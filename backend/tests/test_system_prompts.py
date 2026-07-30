"""Verify every agent ships a readable system prompt."""

from __future__ import annotations

import pytest

from agents.common.utils import load_system_prompt


@pytest.mark.parametrize(
    "agent_name",
    ["orchestrator", "recon", "vuln", "reporter"],
)
def test_system_prompt_exists(agent_name: str) -> None:
    """Each agent folder must contain a non-empty system.md file."""
    prompt = load_system_prompt(agent_name)
    assert prompt
    assert "You are" in prompt
