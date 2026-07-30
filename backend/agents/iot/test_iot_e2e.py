"""End-to-end tests for the IoT/infrastructure security agent."""

from __future__ import annotations

import pytest

from agents.iot.agent import IotState, build_graph
from tests.helpers import allowed_scope, default_settings


@pytest.mark.e2e
def test_e2e_iot_agent_produces_findings() -> None:
    """The IoT agent should return findings for an allowed scope."""
    settings = default_settings()
    graph = build_graph(settings)
    result = graph.invoke(IotState(scope=allowed_scope(settings)))

    assert result.get("error") is None
    assert result.get("findings")
