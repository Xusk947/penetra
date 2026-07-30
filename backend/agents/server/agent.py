"""Server-side security agent."""

from __future__ import annotations

import logging
import operator
from typing import Annotated, Any

from pydantic import BaseModel, Field
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.common.config import Settings
from agents.common.models import Finding
from agents.common.scope import ScopePolicy
from agents.common.tool_findings import run_tool_findings
from tools.vuln.tools import server_tools

logger = logging.getLogger(__name__)


class ServerState(BaseModel):
    """Shared state for the server-side security agent."""

    scope: list[str] = Field(default_factory=list)
    approved: bool = False
    findings: Annotated[list[Finding], operator.add] = Field(default_factory=list)
    error: str | None = None


class ServerAgent:
    """Node callables for the server-side security agent."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._policy = ScopePolicy(settings or Settings())

    def analyze(self, state: ServerState) -> dict[str, Any]:
        """Analyze server-side targets for backend and database issues."""
        if not state.scope:
            return {"error": "No targets provided for server-side analysis"}

        allowed, denied = self._policy.filter_allowed(state.scope, mode="attack")
        if not allowed:
            return {"error": f"All server targets are outside scope: {denied}"}
        if denied:
            logger.warning("Server agent skipped out-of-scope targets: %s", denied)

        findings: list[Finding] = []
        for target in allowed:
            findings.extend(_server_findings(target))

        logger.info("Server-side analysis produced %d findings", len(findings))
        return {"findings": findings}


def _server_findings(target: str) -> list[Finding]:
    """Run the server-side black-box tools against *target* and return findings."""
    return run_tool_findings(server_tools(), target, "server")


def build_graph(
    settings: Settings | None = None,
) -> CompiledStateGraph[ServerState, Any, Any, Any]:
    """Compile the server-side security agent graph."""
    nodes = ServerAgent(settings)

    return (
        StateGraph(ServerState)
        .add_node("analyze", nodes.analyze)
        .add_edge(START, "analyze")
        .add_edge("analyze", END)
        .compile()
    )


graph = build_graph()
