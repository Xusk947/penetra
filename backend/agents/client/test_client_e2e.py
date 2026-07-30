"""End-to-end tests for the client-side security agent."""

from __future__ import annotations

import pytest

from agents.client.agent import build_graph
from agents.client.agent import ClientState
from tests.helpers import allowed_scope, assert_report_ok, default_settings


@pytest.mark.e2e
def test_e2e_client_agent_produces_findings() -> None:
    """The client agent should return findings for an allowed scope."""
    settings = default_settings()
    graph = build_graph(settings)
    result = graph.invoke(ClientState(scope=allowed_scope(settings)))

    assert result.get("error") is None
    assert result.get("findings")
