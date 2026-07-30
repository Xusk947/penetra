"""LangGraph builder for the vulnerability analysis agent."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.vuln.nodes import VulnAgent
from agents.vuln.state import VulnState


def build_graph() -> CompiledStateGraph[VulnState, Any, Any, Any]:
    """Compile the vulnerability analysis agent graph."""
    nodes = VulnAgent()

    return (
        StateGraph(VulnState)
        .add_node("analyze", nodes.analyze)
        .add_edge(START, "analyze")
        .add_edge("analyze", END)
        .compile()
    )
