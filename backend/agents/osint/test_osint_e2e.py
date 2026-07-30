"""End-to-end tests for the OSINT agent."""

from __future__ import annotations

import pytest

from agents.osint.graph import build_graph
from agents.osint.state import OSINTState
from tests.helpers import default_settings, osint_target


@pytest.mark.e2e
def test_e2e_osint_collection() -> None:
    """Run live OSINT against an env-configured target."""
    settings = default_settings()
    if settings.osint_mock:
        pytest.skip("Set OSINT_MOCK=false for live OSINT e2e.")

    graph = build_graph(settings)
    final = graph.invoke(OSINTState(target=osint_target()))

    assert final.get("target") == osint_target()
    assert final.get("results")
