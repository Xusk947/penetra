"""Pentest orchestrator node implementations."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from langchain_core.callbacks import dispatch_custom_event
from pydantic import BaseModel

from agents.client.agent import build_graph as build_client_graph
from agents.common.config import Settings
from agents.common.models import Finding
from agents.common.scope import ScopePolicy
from agents.iot.agent import build_graph as build_iot_graph
from agents.orchestrator.state import OrchestratorState
from agents.reporter.graph import build_graph as build_reporter_graph
from agents.server.agent import build_graph as build_server_graph

logger = logging.getLogger(__name__)

_CLIENT_FOCUS = {
    "client",
    "web",
    "frontend",
    "front",
    "ui",
    "xss",
    "csrf",
    "sqli",
    "sql",
    "клиент",
    "веб",
    "форма",
}
_SERVER_FOCUS = {
    "server",
    "backend",
    "api",
    "config",
    "command",
    "rce",
    "debug",
    "backup",
    "secret",
    "exposed",
    "path",
    "traversal",
    "сервер",
    "бекенд",
    "команда",
    "конфиг",
    "резерв",
    "секрет",
}
_IOT_FOCUS = {
    "iot",
    "device",
    "camera",
    "router",
    "management",
    "admin",
    "default",
    "устройство",
    "камера",
    "роутер",
    "управление",
    "админ",
    "дефолт",
}
_CRED_FOCUS = {
    "cred",
    "access",
    "password",
    "login",
    "auth",
    "weak",
    "credential",
    "доступ",
    "парол",
    "авторизаци",
    "учётк",
    "учетк",
    "логин",
}


def _result_dict(result: object) -> dict[str, Any]:
    """Normalize a compiled graph result to a plain dict."""
    if isinstance(result, dict):
        return result
    if isinstance(result, BaseModel):
        return result.model_dump()
    return {}


def _dedup_findings(findings: list[Finding]) -> list[Finding]:
    """Remove duplicate findings based on title and description."""
    seen: set[tuple[str, str]] = set()
    unique: list[Finding] = []
    for finding in findings:
        key = (finding.title or "", finding.description or "")
        if key not in seen:
            seen.add(key)
            unique.append(finding)
    return unique


def _fresh_config() -> dict[str, Any]:
    """Return a new thread-scoped config that resets inherited checkpoint state."""
    return {"configurable": {"thread_id": str(uuid.uuid4())}}


class Orchestrator:
    """Node callables for the pentest orchestrator."""

    def __init__(
        self,
        settings: Settings,
        nmap_tool: object | None = None,
    ) -> None:
        """Create the orchestrator with its domain agents and reporter."""
        self._settings = settings
        self._policy = ScopePolicy(settings)
        self._client = build_client_graph(settings)
        self._server = build_server_graph(settings)
        self._iot = build_iot_graph(settings)
        self._reporter = build_reporter_graph(settings)

    def validate_scope(self, state: OrchestratorState) -> dict[str, Any]:
        """Confirm the requested scope is within the approved allowlist."""
        logger.info("Validating scope: %s", state.scope)
        approved, error = self._policy.validate(state.scope, mode="attack")
        if not approved:
            return {"error": error, "approved": False}

        allowed, denied = self._policy.filter_allowed(state.scope, mode="attack")
        update: dict[str, Any] = {"approved": True, "scope": allowed}
        if denied:
            update["metadata"] = {"denied_targets": denied}
            logger.warning("Denied targets outside scope: %s", denied)
        return update

    async def _run_domain_agent(
        self,
        state: OrchestratorState,
        agent: object,
        agent_name: str,
    ) -> dict[str, Any]:
        """Invoke a domain agent and merge its findings."""
        if state.error:
            return {"error": state.error}

        dispatch_custom_event(
            "agent_update",
            {"phase": "start", "agent": agent_name, "scope": state.scope},
        )
        result = _result_dict(
            await agent.ainvoke(  # type: ignore[attr-defined]
                {"scope": state.scope, "approved": True},
                config=_fresh_config(),
            )
        )
        findings = result.get("findings", [])
        dispatch_custom_event(
            "agent_update",
            {
                "phase": "end",
                "agent": agent_name,
                "findings_count": len(findings),
                "error": result.get("error"),
            },
        )
        update: dict[str, Any] = {"findings": findings}
        if error := result.get("error"):
            update["error"] = f"{agent_name}: {error}"
        return update

    def _select_agents(self, focus: str) -> list[tuple[str, object]]:
        """Map a free-text focus hint to the domain agents that should run."""
        focus_l = focus.lower()
        agent_keywords = {
            "client": _CLIENT_FOCUS,
            "server": _SERVER_FOCUS,
            "iot": _IOT_FOCUS,
        }

        selected: set[str] = set()
        for agent, keywords in agent_keywords.items():
            if any(kw in focus_l for kw in keywords):
                selected.add(agent)
        if any(kw in focus_l for kw in _CRED_FOCUS):
            selected.update({"server", "iot"})
        if not selected or "all" in focus_l or "system" in focus_l or not focus.strip():
            selected = {"client", "server", "iot"}

        return [
            (name, getattr(self, f"_{name}"))
            for name in ("client", "server", "iot")
            if name in selected
        ]

    async def run_agents(self, state: OrchestratorState) -> dict[str, Any]:
        """Run only the domain agents selected by the focus hint."""
        if not state.approved:
            return {"error": "Scope validation failed; skipping analysis"}

        dispatch_custom_event(
            "agent_update",
            {"phase": "start", "agent": "orchestrator", "scope": state.scope, "focus": state.focus},
        )
        all_findings: list[Finding] = []
        for name, agent in self._select_agents(state.focus):
            result = await self._run_domain_agent(state, agent, name)
            all_findings.extend(result.get("findings", []))
            if error := result.get("error"):
                dispatch_custom_event(
                    "agent_update",
                    {
                        "phase": "end",
                        "agent": "orchestrator",
                        "findings_count": len(all_findings),
                        "error": error,
                    },
                )
                return {"error": error, "findings": _dedup_findings(all_findings)}
        dispatch_custom_event(
            "agent_update",
            {
                "phase": "end",
                "agent": "orchestrator",
                "findings_count": len(all_findings),
            },
        )
        return {"findings": _dedup_findings(all_findings)}

    async def run_report(self, state: OrchestratorState) -> dict[str, Any]:
        """Delegate report generation to the reporter agent."""
        result = _result_dict(
            await self._reporter.ainvoke(  # type: ignore[call-overload]
                {
                    "scope": state.scope,
                    "findings": _dedup_findings(state.findings),
                    "language": state.language,
                },
                config=_fresh_config(),
            )
        )
        update: dict[str, Any] = {
            "report": result.get("report"),
            "finding_reports": result.get("finding_reports", {}),
            "pdf_path": result.get("pdf_path"),
        }
        if error := result.get("error"):
            update["error"] = error
        return update
