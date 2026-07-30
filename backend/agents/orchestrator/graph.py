"""LangGraph builder for the pentest orchestrator."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.common.config import Settings
from agents.orchestrator.nodes import Orchestrator
from agents.orchestrator.state import OrchestratorState


def build_graph(
    settings: Settings | None = None,
    nmap_tool: object | None = None,
) -> CompiledStateGraph[OrchestratorState, Any, Any, Any]:
    """Compile the pentest orchestrator graph."""
    settings = settings or Settings()
    nodes = Orchestrator(settings)

    graph = (
        StateGraph(OrchestratorState)
        .add_node("validate_scope", nodes.validate_scope)
        .add_node("agents", nodes.run_agents)
        .add_node("report", nodes.run_report)
        .add_edge(START, "validate_scope")
        .add_edge("validate_scope", "agents")
        .add_edge("agents", "report")
        .add_edge("report", END)
        .compile()
    )

    return graph
