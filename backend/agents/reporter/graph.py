"""LangGraph builder for the report writer agent."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.common.config import Settings
from agents.reporter.nodes import ReporterAgent
from agents.reporter.state import ReportState


def build_graph(settings: Settings | None = None) -> CompiledStateGraph[ReportState, Any, Any, Any]:
    """Compile the report writer agent graph.

    The graph first renders the markdown report (``generate``), then persists
    it to disk as markdown/PDF along with a per-finding trace file for each
    vulnerability, and attempts remote delivery (``export``).
    """
    nodes = ReporterAgent(settings)

    return (
        StateGraph(ReportState)
        .add_node("generate", nodes.generate)
        .add_node("export", nodes.export)
        .add_edge(START, "generate")
        .add_edge("generate", "export")
        .add_edge("export", END)
        .compile()
    )
