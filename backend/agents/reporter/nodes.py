"""Report writer agent node implementations."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.common.config import Settings
from agents.reporter.delivery import deliver_report
from agents.reporter.pdf import render_report_pdf
from agents.reporter.render import (
    build_report_markdown,
    localize_report,
    resolve_language,
)
from agents.reporter.state import ReportState
from agents.reporter.trace import render_finding_trace

logger = logging.getLogger(__name__)


class ReporterAgent:
    """Node callables for the report writer agent."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()

    def generate(self, state: ReportState) -> dict[str, Any]:
        """Produce a human-readable summary from the collected findings."""
        if state.error:
            return {"report": f"## Scan Error\n\n{state.error}"}
        language = resolve_language(state.language)
        report = build_report_markdown(state.findings, state.scope)
        if language != "en":
            report = localize_report(report, language, self._settings)
        return {"report": report}

    def export(self, state: ReportState) -> dict[str, Any]:
        """Persist the report as markdown/PDF and per-finding trace files locally.

        Delivery to a remote destination is attempted afterwards (currently a
        no-op stub until a concrete remote endpoint is configured).
        """
        if not state.report:
            return {}

        reports_dir = Path(self._settings.reports_dir)
        run_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        report_md_path = reports_dir / f"pentest_{run_stamp}.md"
        report_md_path.parent.mkdir(parents=True, exist_ok=True)
        report_md_path.write_text(state.report, encoding="utf-8")

        # Per-finding mini-reports so each vulnerability can be reviewed
        # independently, with its own ID and discovery trace.
        finding_reports: dict[str, str] = {}
        findings_dir = reports_dir / "findings"
        findings_dir.mkdir(parents=True, exist_ok=True)
        for finding in state.findings:
            trace_path = findings_dir / f"{finding.id}.md"
            trace_path.write_text(render_finding_trace(finding), encoding="utf-8")
            finding_reports[finding.id] = str(trace_path)

        if state.error:
            return {"finding_reports": finding_reports}

        pdf_path = reports_dir / f"pentest_{run_stamp}.pdf"
        try:
            render_report_pdf(
                state.scope,
                state.findings,
                pdf_path,
                report_text=state.report,
                language=resolve_language(state.language),
            )
        except Exception as exc:
            logger.warning("Failed to render PDF report: %s", exc)
            return {"finding_reports": finding_reports}

        deliver_report(pdf_path, self._settings)

        return {"finding_reports": finding_reports, "pdf_path": str(pdf_path)}
