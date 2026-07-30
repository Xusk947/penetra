"""Tools available to the frontdesk chat agent."""

from __future__ import annotations

import re
import uuid
from typing import Annotated, Any

import anyio
from langchain.tools import ToolRuntime
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from agents.common.config import Settings
from agents.common.constants import (
    DEFAULT_PUBLIC_TARGET,
    OSINT_SUMMARY_PREFIX,
    RESEARCH_SUMMARY_PREFIX,
    TEXT_SNIPPET_LENGTH,
)
from agents.common.logging_config import configure_run_logging
from agents.orchestrator.graph import build_graph as build_orchestrator_graph
from agents.orchestrator.state import OrchestratorState
from agents.osint.graph import build_graph as build_osint_graph
from agents.osint.state import OSINTState
from agents.reporter.render import localize_findings, resolve_language
from agents.research.graph import build_graph as build_research_graph
from agents.research.state import ResearchState
from db.reports import SessionLocal, init_db, save_report

_LANGUAGE_DESC = (
    "ISO 639-1 language code for the report (e.g. 'en', 'ru', 'es'). "
    "Use 'auto' to detect the language from the user's message "
    "(fallback: English)."
)
_SCOPE_DESC = (
    "Approved target scope: list of IPs, hostnames or URLs. "
    "Defaults to the configured TARGET_HOST."
)
_FOCUS_DESC = (
    "Intent hint for the pentest. Use keywords like 'backend/server', "
    "'client/web', 'iot/management', 'credentials/access' or 'all'. "
    "This lets the orchestrator run only the relevant domain agents."
)


def _extract_thread_and_run_ids(
    config: RunnableConfig | None,
) -> tuple[str | None, str | None]:
    """Pull thread/run IDs from the runnable config, if available."""
    if not isinstance(config, dict):
        return None, None

    thread_id = config.get("configurable", {}).get("thread_id")
    run_id = config.get("run_id") or config.get("configurable", {}).get("run_id")
    return thread_id, run_id


_CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")


def _message_text(content: Any) -> str:
    """Flatten a message content value (string or block list) to plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return ""


def _detect_user_language(runtime: ToolRuntime | None) -> str | None:
    """Detect the report language from the last user message in agent state.

    Deterministic fallback for when the LLM forgets to pass the ``language``
    tool argument. Currently maps Cyrillic script to ``ru``; returns None
    when no user message is found or no known script is detected.
    """
    if runtime is None:
        return None
    state = getattr(runtime, "state", None) or {}
    messages = state.get("messages") if isinstance(state, dict) else None
    if not messages:
        return None
    for message in reversed(messages):
        if getattr(message, "type", None) not in ("human", "user"):
            continue
        text = _message_text(getattr(message, "content", ""))
        if _CYRILLIC_RE.search(text):
            return "ru"
        return None
    return None


def _resolve_report_language(language: str | None, runtime: ToolRuntime | None) -> str:
    """Resolve the report language, falling back to user-message detection."""
    resolved = resolve_language(language)
    if language and language.strip().lower() not in ("auto", ""):
        return resolved
    return _detect_user_language(runtime) or resolved


def _serialize_findings(raw_findings: Any) -> list[dict[str, Any]] | None:
    """Serialize orchestrator findings (pydantic models or dicts) to plain dicts."""
    if not raw_findings:
        return None
    serialized: list[dict[str, Any]] = []
    for finding in raw_findings:
        if hasattr(finding, "model_dump"):
            serialized.append(finding.model_dump())
        elif isinstance(finding, dict):
            serialized.append(dict(finding))
    return serialized or None


def _persist_report(
    report_text: str,
    thread_id: str | None,
    run_id: str | None,
    scope: list[str],
    focus: str,
    language: str,
    request_prompt: str | None,
    result: dict[str, Any],
) -> str:
    """Persist the report to the database and return its ID."""
    init_db()
    with SessionLocal() as session:
        findings = _serialize_findings(result.get("findings"))
        if findings and resolve_language(language) != "en":
            # The frontend report page renders structured findings, so they
            # must be localized too — the markdown alone is not enough.
            findings = localize_findings(findings, language, Settings())
        findings_count = (
            len(findings)
            if findings is not None
            else len(result.get("finding_reports") or {})
        )
        report = save_report(
            session,
            markdown=report_text,
            thread_id=thread_id,
            run_id=run_id,
            scope=scope,
            focus=focus,
            language=language,
            title=f"Pentest report: {', '.join(scope)}",
            pdf_path=result.get("pdf_path"),
            finding_reports=result.get("finding_reports"),
            findings_count=findings_count,
            request_prompt=request_prompt,
            findings=findings,
        )
        return report.id


class RunPentestInput(BaseModel):
    """Input schema for the run_pentest tool (the config key is injected)."""

    scope: list[str] | None = Field(default=None, description=_SCOPE_DESC)
    language: str = Field(default="auto", description=_LANGUAGE_DESC)
    focus: str = Field(default="all", description=_FOCUS_DESC)


@tool(args_schema=RunPentestInput, infer_schema=False)
async def run_pentest(
    scope: list[str] | None = None,
    language: str = "auto",
    focus: str = "all",
    config: RunnableConfig = None,  # type: ignore[assignment]
    runtime: ToolRuntime = None,  # type: ignore[assignment]
) -> str:
    """Run the authorized pentest workflow and return a report.

    If *scope* is omitted, the configured `TARGET_HOST` from `.env` is used.
    The report is generated in the user's language: pass *language* explicitly
    (e.g. 'ru' for Russian) or leave it as 'auto' to detect it from the
    user's message (fallback: English).

    Use *focus* to tell the orchestrator which domain agents to run
    (e.g. 'backend' for server-side checks, 'client' for web UI checks,
    'iot' for management interfaces, 'credentials' for weak/default creds).
    """
    if not scope:
        target = Settings().target_host or DEFAULT_PUBLIC_TARGET
        scope = [target]

    language = _resolve_report_language(language, runtime)

    log_path = await anyio.to_thread.run_sync(configure_run_logging)
    orchestrator_graph = await anyio.to_thread.run_sync(
        build_orchestrator_graph, Settings()
    )

    thread_id, run_id = _extract_thread_and_run_ids(config)
    orchestrator_config = {"configurable": {"thread_id": thread_id or str(uuid.uuid4())}}
    result = await orchestrator_graph.ainvoke(
        OrchestratorState(scope=scope, language=language, focus=focus),
        config=orchestrator_config,
    )
    report_text = result.get("report") or "No report was generated."

    request_prompt = None
    report_id = await anyio.to_thread.run_sync(
        _persist_report,
        report_text,
        thread_id,
        run_id,
        scope,
        focus,
        language,
        request_prompt,
        dict(result),
    )

    notes = [
        f"Report ID: {report_id}",
        f"Report API: /reports/{report_id}",
        f"Full run log (every agent/tool action, recorded live) saved at: {log_path}",
    ]
    if pdf_path := result.get("pdf_path"):
        notes.append(f"A PDF copy of this report was saved locally at: {pdf_path}")
    if finding_reports := result.get("finding_reports"):
        notes.append(
            f"Each of the {len(finding_reports)} findings has its own traceable "
            "mini-report (finding ID, agent, tool, and discovery steps) saved under "
            "reports/findings/<finding-id>.md."
        )
    report = report_text + "\n\n---\n" + "\n".join(notes)
    return report


@tool
async def run_osint(
    target: Annotated[
        str,
        "Approved target for passive OSINT (domain or IP).",
    ],
) -> str:
    """Run passive OSINT collection against the target and return a structured summary."""
    if not target:
        return "Error: no target provided."

    result = await build_osint_graph().ainvoke(
        OSINTState(target=target),
        config={"configurable": {"thread_id": str(uuid.uuid4())}},
    )
    results = result.get("results", {})
    if not results:
        return "No OSINT sources are currently configured. Add API keys to .env to enable them."

    lines = [f"{OSINT_SUMMARY_PREFIX} for {target}:\n"]
    for source, data in results.items():
        error = data.get("error")
        if error:
            lines.append(f"- **{source}**: skipped ({error})")
        else:
            lines.append(f"- **{source}**: collected {len(data.get('data', {}))} fields")
    return "\n".join(lines)


@tool
async def run_research(
    url: Annotated[
        str,
        "URL to fetch and summarize for research purposes.",
    ],
) -> str:
    """Use the research browser to fetch and summarize a public web page."""
    if not url:
        return "Error: no URL provided."

    result = await build_research_graph().ainvoke(
        ResearchState(target=url),
        config={"configurable": {"thread_id": str(uuid.uuid4())}},
    )
    if result.get("error"):
        return f"Research failed: {result['error']}"

    lines = [f"{RESEARCH_SUMMARY_PREFIX} for {url}:", ""]
    if title := result.get("page_title"):
        lines.append(f"**Title:** {title}")
    if summary := result.get("summary"):
        lines.append(f"**Summary:** {summary}")
    if text := result.get("page_text"):
        lines.append(f"**Text snippet:** {text[:TEXT_SNIPPET_LENGTH]}")
    if links := result.get("links"):
        lines.append(f"**Links found:** {len(links)}")
    return "\n".join(lines)
