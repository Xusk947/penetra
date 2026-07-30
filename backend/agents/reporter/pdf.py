"""PDF rendering for the pentest report.

The renderer builds an HTML page from the markdown report using the same
Manrope / JetBrains Mono variable fonts and CSS variables as the frontend, then
uses Playwright to generate a PDF. This keeps the PDF visually consistent with
the web UI and correctly renders non-ASCII characters.
"""

from __future__ import annotations

import logging
from pathlib import Path

from agents.common.constants import REPORT_TITLE
from agents.common.models import Finding
from services.pdf_renderer import render_markdown_to_pdf

logger = logging.getLogger(__name__)


def render_report_pdf(
    scope: list[str],
    findings: list[Finding],
    output_path: Path,
    report_text: str | None = None,
    language: str = "en",
) -> Path:
    """Render the full pentest report as a styled PDF and save it to *output_path*.

    *report_text* is the localized markdown report. If it is missing, falls back
    to generating a minimal markdown string from the findings. The *language*
    argument is accepted for API compatibility but the PDF is produced from the
    supplied markdown regardless of language.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    markdown_text = report_text or _findings_to_markdown(scope, findings)

    return render_markdown_to_pdf(
        markdown_text,
        output_path,
        title=REPORT_TITLE,
        scope=scope,
        findings_count=len(findings),
    )


def _findings_to_markdown(scope: list[str], findings: list[Finding]) -> str:
    """Fallback markdown builder when no pre-rendered report text is available."""
    lines = [f"# {REPORT_TITLE}", "", f"**Scope:** {', '.join(scope)}", ""]
    if not findings:
        lines.append("No findings.")
        return "\n".join(lines)

    lines.append(f"**Findings:** {len(findings)}")
    for finding in findings:
        lines.append(f"\n## [{finding.id}] {finding.title}")
        lines.append(f"- **Severity:** {finding.severity}")
        lines.append(f"- **Agent:** {finding.agent or 'n/a'}")
        lines.append(f"- **Tool:** {finding.tool or 'n/a'}")
        lines.append(f"- **Score:** {finding.score}/5")
        lines.append("")
        lines.append(finding.description or "")
    return "\n".join(lines)
