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
    """Return a short writing-style note for the frontdesk prompt.

    Loading the full avoid-ai-writing SKILL.md (~75 KB) into every frontdesk
    call bloats the prompt to ~19k tokens and makes even simple messages slow.
    We keep only the practical takeaway: be direct, avoid AI clichés, and write
    in the user's language.
    """
    return (
        "Write in the user's language. Be direct and concise. "
        "Avoid generic AI phrases like 'delve', 'leverage', 'in today's digital age', "
        "or over-confident claims. Answer only what was asked."
    )


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
