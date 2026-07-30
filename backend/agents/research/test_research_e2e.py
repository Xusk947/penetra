"""End-to-end tests for the research browser agent."""

from __future__ import annotations

import os

import pytest

from agents.research.graph import build_graph
from agents.research.state import ResearchState
from tests.helpers import assert_research_page_ok, default_settings, research_url


@pytest.mark.e2e
def test_e2e_research_browser_fetches_page() -> None:
    """Fetch a real web page with the research browser when configured for live mode."""
    settings = default_settings()

    if settings.research_mock and os.getenv("RESEARCH_URL") is None:
        pytest.skip("Set RESEARCH_MOCK=false and RESEARCH_URL for live research e2e.")

    # If the user set RESEARCH_URL but left RESEARCH_MOCK=true, force live mode.
    if settings.research_mock:
        settings = settings.model_copy(update={"research_mock": False})

    graph = build_graph(settings)
    result = graph.invoke(ResearchState(target=research_url()))
    assert_research_page_ok(result)
