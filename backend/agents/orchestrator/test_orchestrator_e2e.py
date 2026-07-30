"""End-to-end tests for the orchestrator agent."""

from __future__ import annotations

import pytest

from agents.orchestrator.graph import build_graph
from agents.orchestrator.state import OrchestratorState
from tests.helpers import allowed_scope, assert_report_ok, assert_scope_denied, default_settings, denied_target


@pytest.mark.e2e
def test_e2e_orchestrator_produces_report() -> None:
    """Run the full pentest cycle with the env-configured allowed scope."""
    settings = default_settings()
    graph = build_graph(settings)
    final = graph.invoke(OrchestratorState(scope=allowed_scope(settings)))
    assert_report_ok(final)


@pytest.mark.e2e
def test_e2e_orchestrator_denies_out_of_scope_target() -> None:
    """A target outside the attack scope must be rejected by the orchestrator."""
    settings = default_settings()
    target = denied_target(settings)

    if target in allowed_scope(settings):
        pytest.skip(f"Target {target!r} is in the allowed scope; cannot test denial.")

    graph = build_graph(settings)
    final = graph.invoke(OrchestratorState(scope=[target]))
    assert_scope_denied(final)
