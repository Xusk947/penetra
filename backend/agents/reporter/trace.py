"""Per-finding trace report generation.

Every finding is traceable back to the domain agent and tool/check that
produced it. This module renders a small standalone markdown report per
finding so each vulnerability can be reviewed independently of the full
pentest report.
"""

from __future__ import annotations

from agents.common.models import Finding


def render_finding_trace(finding: Finding) -> str:
    """Render a standalone markdown mini-report for a single finding."""
    lines = [f"# {finding.id}: {finding.title}", ""]
    lines.append(f"- **Finding ID**: {finding.id}")
    lines.append(f"- **Agent**: {finding.agent or 'unknown'}")
    lines.append(f"- **Tool/check**: {finding.tool or 'unknown'}")
    lines.append(f"- **Category**: {finding.category or 'general'}")
    lines.append(f"- **Severity**: {finding.severity}")
    lines.append(f"- **Score**: {finding.score}/5" if finding.score else "- **Score**: n/a")
    lines.append(f"- **Confidence**: {finding.confidence}")
    if finding.cwe:
        lines.append(f"- **CWE**: {finding.cwe}")
    lines.append("")

    lines.append("## Description")
    lines.append(finding.description)
    lines.append("")

    lines.append("## Trace: how this was discovered")
    if finding.steps:
        for idx, step in enumerate(finding.steps, start=1):
            lines.append(f"{idx}. {step}")
    else:
        lines.append("No step-by-step trace was recorded for this finding.")
    lines.append("")

    if finding.remediation:
        lines.append("## Remediation")
        lines.append(finding.remediation)
        lines.append("")

    return "\n".join(lines)
