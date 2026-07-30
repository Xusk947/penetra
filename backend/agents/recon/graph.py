"""LangGraph builder for the reconnaissance agent."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.recon.nodes import ReconAgent
from agents.recon.state import ReconState
from tools.recon.nmap import NmapTool


def build_graph(
    nmap_tool: NmapTool | None = None,
) -> CompiledStateGraph[ReconState, Any, Any, Any]:
    """Compile the reconnaissance agent graph."""
    nodes = ReconAgent(nmap_tool or NmapTool(mock=True))

    return (
        StateGraph(ReconState)
        .add_node("validate_scope", nodes.validate_scope)
        .add_node("scan", nodes.scan)
        .add_edge(START, "validate_scope")
        .add_edge("validate_scope", "scan")
        .add_edge("scan", END)
        .compile()
    )
