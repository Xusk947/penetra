"""Smoke tests for the multi-agent pentest workflow."""

from __future__ import annotations

import asyncio

from agents.orchestrator.graph import build_graph
from agents.orchestrator.state import OrchestratorState
from tests.helpers import DEFAULT_PUBLIC_TARGET, EXPECTED_FINDINGS_SECTION, EXPECTED_REPORT_TITLE


def test_empty_scope_returns_error() -> None:
    """An empty scope should stop the workflow with an error."""
    graph = build_graph()
    final = asyncio.run(graph.ainvoke(OrchestratorState(scope=[])))

    assert final["approved"] is False
    assert final["error"] is not None


def test_graph_runs_client_server_iot_and_report() -> None:
    """A valid scope should run all three domain agents and produce a report."""
    graph = build_graph()
    final = asyncio.run(graph.ainvoke(OrchestratorState(scope=[DEFAULT_PUBLIC_TARGET])))

    assert final["approved"] is True
    assert final["report"] is not None
    assert final["findings"] is not None
    assert EXPECTED_REPORT_TITLE in final["report"]
    if final["findings"]:
        assert EXPECTED_FINDINGS_SECTION in final["report"]
    else:
        assert "No findings." in final["report"]
    assert final.get("error") is None
