"""Tests for the research browser agent."""

from __future__ import annotations

from agents.research.graph import build_graph
from agents.research.state import ResearchState
from tests.helpers import DEFAULT_RESEARCH_URL, LOOPBACK_IP


def test_research_agent_fetches_mock_page() -> None:
    """The research agent should return page metadata in mock mode."""
    graph = build_graph()
    result = graph.invoke(ResearchState(target=DEFAULT_RESEARCH_URL))

    assert result.get("error") is None
    assert result.get("page_title") is not None
    assert result.get("page_text")
    assert result.get("links")


def test_research_agent_blocks_private_ip() -> None:
    """The research browser must not fetch private/reserved IPs."""
    graph = build_graph()
    result = graph.invoke(ResearchState(target=f"http://{LOOPBACK_IP}"))

    assert result.get("error") is not None
