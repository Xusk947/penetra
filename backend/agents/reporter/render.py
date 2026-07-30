"""Deterministic markdown rendering for pentest reports.

Extracted from ``ReporterAgent.generate`` so the same report format (including
localization) can be rebuilt after a manual findings edit (see
``reports_api.py``).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage

from agents.common.config import Settings
from agents.common.constants import (
    DEFAULT_CATEGORY,
    DEFAULT_SCORE,
    DETAILED_FINDINGS_TITLE,
    EXECUTIVE_SUMMARY_TITLE,
    FINDINGS_INDEX_TITLE,
    MAX_SCORE,
    REPORT_TITLE_MARKDOWN,
)
from agents.common.llm import get_chat_model
from agents.common.models import Finding

logger = logging.getLogger(__name__)


def severity_label(severity: str) -> str:
    """Return the normalized English severity label for reports."""
    return severity.lower()


def resolve_language(code: str | None) -> str:
    """Normalize a language code; unsupported/empty values fall back to 'en'."""
    if not code:
        return "en"
    code = code.strip().lower()
    if code in ("auto", ""):
        return "en"
    if len(code) == 2 and code.isalpha():
        return code
    logger.warning("Unsupported language code %r; using 'en'", code)
    return "en"


def localize_report(
    report: str, language: str, settings: Settings | None = None
) -> str:
    """Translate *report* into *language* using the configured chat model.

    Falls back to the original English report if the model is unavailable
    or the translation call fails.
    """
    language = resolve_language(language)
    if language == "en" or not report:
        return report

    try:
        model = get_chat_model(settings or Settings())
    except RuntimeError as exc:
        logger.warning("Cannot localize report: %s. Using English.", exc)
        return report

    prompt = (
        f"Translate the following pentest report from English into the language "
        f"identified by the ISO 639-1 code '{language}'. "
        "Translate only human-readable prose (report title, section headings, "
        "descriptions, remediation text, and trace steps). "
        "Keep the following elements in English exactly as they appear, "
        "including spelling and case:\n"
        "- all markdown table headers "
        "(e.g. '| ID | Title | Severity | Agent | Tool |')\n"
        "- all field labels (e.g. 'Severity', 'Confidence', 'Category', "
        "'Agent', 'Tool', 'Score', 'CWE', 'Description', 'Remediation', "
        "'Trace', 'Scope', 'Findings', 'Finding ID')\n"
        "- all severity values: critical, high, medium, low, info\n"
        "- all confidence values: certain, high, medium, low\n"
        "- all agent names (client, server, iot), tool/check names, "
        "and category values\n"
        "- all finding IDs (VULN-XXXXXXXX), CWE identifiers (CWE-NNN), "
        "scores (X/5), and scope values\n"
        "- all code snippets, URLs, IP addresses, file paths, and credentials\n"
        "Do not add any extra commentary. "
        "Return only the translated markdown report.\n\n"
        f"```markdown\n{report}\n```"
    )
    try:
        response = model.invoke([HumanMessage(content=prompt)])
    except Exception as exc:
        logger.warning("Report localization failed: %s. Using English.", exc)
        return report

    localized = response.content
    if not isinstance(localized, str):
        logger.warning("Report localization returned non-string content; using English.")
        return report

    return localized.strip() or report


_FINDING_PROSE_FIELDS = ("title", "description", "remediation", "steps")


def _extract_json(text: str) -> Any:
    """Parse JSON from a model response, tolerating markdown code fences."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return json.loads(text)


def localize_findings(
    findings: list[dict[str, Any]], language: str, settings: Settings | None = None
) -> list[dict[str, Any]]:
    """Translate the human-readable fields of structured *findings*.

    The frontend report page renders structured findings (not the markdown),
    so without this the cards would always stay in English. Translates
    ``title``/``description``/``remediation``/``steps`` in a single batched
    LLM call; falls back to the original findings on any failure.
    """
    language = resolve_language(language)
    if language == "en" or not findings:
        return findings

    try:
        model = get_chat_model(settings or Settings())
    except RuntimeError as exc:
        logger.warning("Cannot localize findings: %s. Using English.", exc)
        return findings

    payload = [
        {
            "id": finding.get("id"),
            "title": finding.get("title"),
            "description": finding.get("description"),
            "remediation": finding.get("remediation"),
            "steps": finding.get("steps") or [],
        }
        for finding in findings
    ]
    prompt = (
        "Translate the following JSON array of pentest findings from English "
        f"into the language identified by the ISO 639-1 code '{language}'. "
        "Return a JSON array with the exact same length, order, keys and "
        "'id' values. Translate only the 'title', 'description', "
        "'remediation' and 'steps' prose. Keep URLs, IP addresses, file "
        "paths, code snippets, commands, and credentials untranslated. "
        "Return only valid JSON, no commentary.\n\n"
        f"```json\n{json.dumps(payload, ensure_ascii=False)}\n```"
    )
    try:
        response = model.invoke([HumanMessage(content=prompt)])
        content = response.content
        if not isinstance(content, str):
            raise ValueError("non-string model response")
        translated = _extract_json(content)
        if not isinstance(translated, list) or len(translated) != len(findings):
            raise ValueError("translated payload shape mismatch")
        by_id = {
            item.get("id"): item for item in translated if isinstance(item, dict)
        }
    except Exception as exc:
        logger.warning("Findings localization failed: %s. Using English.", exc)
        return findings

    localized: list[dict[str, Any]] = []
    for finding in findings:
        item = by_id.get(finding.get("id"))
        if not item:
            localized.append(finding)
            continue
        merged = dict(finding)
        for field in _FINDING_PROSE_FIELDS:
            if item.get(field):
                merged[field] = item[field]
        localized.append(merged)
    return localized


def build_report_markdown(findings: list[Finding], scope: list[str]) -> str:
    """Build the full English markdown report from structured findings."""
    lines = [REPORT_TITLE_MARKDOWN, ""]
    lines.append(f"**Scope:** {', '.join(scope)}")
    lines.append(f"**Findings:** {len(findings)}")
    lines.append("")

    if not findings:
        lines.append("No findings.")
        return "\n".join(lines)

    lines.append(EXECUTIVE_SUMMARY_TITLE)
    lines.append("")
    by_category: dict[str, list[Finding]] = {}
    for finding in findings:
        by_category.setdefault(finding.category or DEFAULT_CATEGORY, []).append(finding)

    for category, category_findings in by_category.items():
        avg_score = sum(f.score or DEFAULT_SCORE for f in category_findings) / len(
            category_findings
        )
        lines.append(
            f"- **{category.upper()}**: {len(category_findings)} findings, "
            f"average score {avg_score:.1f}/{MAX_SCORE}"
        )
    lines.append("")

    # Findings index: quick-reference table so each finding can be looked
    # up independently by ID, and to see at a glance which agent/tool
    # produced it.
    lines.append(FINDINGS_INDEX_TITLE)
    lines.append("")
    lines.append("| ID | Title | Severity | Agent | Tool |")
    lines.append("|---|---|---|---|---|")
    for finding in findings:
        lines.append(
            f"| {finding.id} | {finding.title} | {severity_label(finding.severity)} "
            f"| {finding.agent or 'n/a'} | {finding.tool or 'n/a'} |"
        )
    lines.append("")

    lines.append(DETAILED_FINDINGS_TITLE)
    for idx, finding in enumerate(findings, start=1):
        score = finding.score or DEFAULT_SCORE
        lines.append(f"### {idx}. [{finding.id}] {finding.title}")
        lines.append(f"- **Finding ID**: {finding.id}")
        lines.append(f"- **Agent**: {finding.agent or 'unknown'}")
        lines.append(f"- **Tool/check**: {finding.tool or 'unknown'}")
        lines.append(f"- **Category**: {finding.category or 'general'}")
        lines.append(f"- **Severity**: {severity_label(finding.severity)}")
        lines.append(f"- **Score**: {score}/{MAX_SCORE}")
        lines.append(f"- **Confidence**: {finding.confidence}")
        if finding.cwe:
            lines.append(f"- **CWE**: {finding.cwe}")
        lines.append("")
        lines.append(f"**Description:** {finding.description}")
        lines.append("")
        if finding.steps:
            lines.append("**Trace (steps taken):**")
            for step_idx, step in enumerate(finding.steps, start=1):
                lines.append(f"{step_idx}. {step}")
            lines.append("")
        if finding.remediation:
            lines.append(f"**Remediation:** {finding.remediation}")
            lines.append("")

    return "\n".join(lines)
