"""LangGraph builder for the passive OSINT agent."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.common.config import Settings
from agents.osint.nodes import OSINTAgent
from agents.osint.state import OSINTState


def build_graph(
    settings: Settings | None = None,
) -> CompiledStateGraph[OSINTState, Any, Any, Any]:
    """Compile the passive OSINT agent graph."""
    settings = settings or Settings()
    nodes = OSINTAgent(settings)

    return (
        StateGraph(OSINTState)
        .add_node("collect", nodes.collect)
        .add_edge(START, "collect")
        .add_edge("collect", END)
        .compile()
    )
