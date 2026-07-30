"""LangGraph builder for the research browser agent."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.common.config import Settings
from agents.research.nodes import ResearchAgent
from agents.research.state import ResearchState


def build_graph(
    settings: Settings | None = None,
) -> CompiledStateGraph[ResearchState, Any, Any, Any]:
    """Compile the research browser agent graph."""
    nodes = ResearchAgent(settings)

    return (
        StateGraph(ResearchState)
        .add_node("browse", nodes.browse)
        .add_edge(START, "browse")
        .add_edge("browse", END)
        .compile()
    )
