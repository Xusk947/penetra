"""IoT / infrastructure security agent."""

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
from tools.vuln.tools import iot_tools

logger = logging.getLogger(__name__)


class IotState(BaseModel):
    """Shared state for the IoT/infrastructure security agent."""

    scope: list[str] = Field(default_factory=list)
    approved: bool = False
    findings: Annotated[list[Finding], operator.add] = Field(default_factory=list)
    error: str | None = None


class IotAgent:
    """Node callables for the IoT/infrastructure security agent."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._policy = ScopePolicy(settings or Settings())

    def analyze(self, state: IotState) -> dict[str, Any]:
        """Analyze IoT, server, and infrastructure targets."""
        if not state.scope:
            return {"error": "No targets provided for IoT/infrastructure analysis"}

        allowed, denied = self._policy.filter_allowed(state.scope, mode="attack")
        if not allowed:
            return {"error": f"All IoT targets are outside scope: {denied}"}
        if denied:
            logger.warning("IoT agent skipped out-of-scope targets: %s", denied)

        findings: list[Finding] = []
        for target in allowed:
            findings.extend(_iot_findings(target))

        logger.info("IoT/infrastructure analysis produced %d findings", len(findings))
        return {"findings": findings}


def _iot_findings(target: str) -> list[Finding]:
    """Run the IoT/infrastructure black-box tools against *target* and return findings."""
    return run_tool_findings(iot_tools(), target, "iot")


def build_graph(
    settings: Settings | None = None,
) -> CompiledStateGraph[IotState, Any, Any, Any]:
    """Compile the IoT/infrastructure security agent graph."""
    nodes = IotAgent(settings)

    return (
        StateGraph(IotState)
        .add_node("analyze", nodes.analyze)
        .add_edge(START, "analyze")
        .add_edge("analyze", END)
        .compile()
    )


graph = build_graph()
