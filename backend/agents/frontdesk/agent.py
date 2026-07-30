"""Frontdesk chat agent entry point."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langgraph.graph.state import CompiledStateGraph

from agents.common.config import Settings
from agents.common.constants import DEFAULT_PUBLIC_TARGET
from agents.common.llm import get_chat_model
from agents.common.utils import load_system_prompt
from agents.frontdesk.tools import run_osint, run_pentest, run_research
from tools.osint.tools import get_osint_tools_summary


def _load_writing_style_skill() -> str:
    """Load the avoid-ai-writing SKILL.md from known locations, if present.

    The project copy at the repository root is preferred; fall back to the
    Claude skills directory so the same file can be picked up in different
    environments.
    """
    candidates = [
        Path(__file__).resolve().parents[3] / "avoid-ai-writing" / "SKILL.md",
        Path(__file__).resolve().parents[3]
        / ".claude"
        / "skills"
        / "avoid-ai-writing"
        / "SKILL.md",
        Path.home() / ".claude" / "skills" / "avoid-ai-writing" / "SKILL.md",
    ]
    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
    return ""


def _build_system_prompt() -> str:
    """Load the static system prompt and inject the current target, OSINT tools, and writing style skill."""
    settings = Settings()
    target_host = settings.target_host or DEFAULT_PUBLIC_TARGET
    target_url = settings.target_url or f"https://{target_host}"
    base = load_system_prompt("frontdesk")
    return base.format(
        avoid_ai_writing_skill=_load_writing_style_skill(),
        osint_tools=get_osint_tools_summary(settings),
        target_host=target_host,
        target_url=target_url,
    )


def make_graph() -> CompiledStateGraph[Any, Any, Any, Any]:
    """Build the frontdesk chat agent graph.

    This is a factory function so LangGraph can rebuild the graph per request
    and pick up the latest ``OPENROUTER_API_KEY`` and OSINT configuration
    from the environment.
    """
    system_prompt = _build_system_prompt()
    tools = [run_pentest, run_osint, run_research]

    return create_agent(
        get_chat_model(),
        tools,
        system_prompt=system_prompt,
    )
