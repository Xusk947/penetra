"""Tests for the frontdesk chat agent."""

from __future__ import annotations

import asyncio

from agents.frontdesk.tools import run_osint, run_pentest, run_research
from tests.helpers import (
    DEFAULT_PUBLIC_TARGET,
    DEFAULT_RESEARCH_URL,
    EXPECTED_OSINT_PREFIX,
    EXPECTED_REPORT_TITLE,
    EXPECTED_RESEARCH_PREFIX,
)


def test_run_pentest_tool_returns_report() -> None:
    """The run_pentest tool should invoke the orchestrator and return a report."""
    result = asyncio.run(run_pentest.ainvoke({"scope": [DEFAULT_PUBLIC_TARGET]}))

    assert isinstance(result, str)
    assert EXPECTED_REPORT_TITLE in result


def test_run_osint_tool_returns_summary() -> None:
    """The run_osint tool should invoke the OSINT agent and summarize results."""
    result = asyncio.run(run_osint.ainvoke({"target": DEFAULT_PUBLIC_TARGET}))

    assert isinstance(result, str)
    assert EXPECTED_OSINT_PREFIX in result


def test_run_research_tool_returns_summary() -> None:
    """The run_research tool should invoke the research browser and return a summary."""
    result = asyncio.run(run_research.ainvoke({"url": DEFAULT_RESEARCH_URL}))

    assert isinstance(result, str)
    assert EXPECTED_RESEARCH_PREFIX in result


def test_frontdesk_graph_factory(monkeypatch) -> None:
    """The frontdesk factory should produce a compiled graph when the API key is set."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy-key-for-tests")
    from agents.frontdesk.agent import make_graph

    graph = make_graph()
    assert graph is not None
