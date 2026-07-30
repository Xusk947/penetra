"""Shared helpers for running black-box tools and normalizing their output.

Each domain agent (client/server/iot) invokes a list of LangChain tools against
a target. Vulnerability-check tools return actual ``Finding``-shaped results;
generic recon tools (curl, playwright, endpoint fuzzer, nmap, tech detector,
python sandbox, ...) return raw telemetry that is useful for live logging and
debugging but is not itself a vulnerability. Only the former should ever
become a ``Finding`` in the report — raw recon output is logged (it already
shows up in the per-run log file via each tool's own HTTP/tool logging) but is
never turned into a synthetic "info" finding, to keep the findings list free
of noise.

This module centralizes that logic so every real finding is tagged with the
domain agent and the specific tool/check that produced it, giving a full
trace of how each finding was discovered.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from langchain_core.callbacks import dispatch_custom_event

from agents.common.models import Finding

logger = logging.getLogger(__name__)


def _is_finding_dict(item: Any) -> bool:
    """Return True if *item* looks like a serialized ``Finding``."""
    return isinstance(item, dict) and all(
        k in item for k in ("title", "severity", "confidence", "description")
    )


def _parse_tool_result(tool_name: str, raw: Any, agent_name: str) -> list[Finding]:
    """Extract only genuine ``Finding``-shaped results from a tool's output.

    Recon/telemetry tools that don't report an actual vulnerability (e.g.
    ``curl``, ``playwright_browser``, ``endpoint_fuzzer``, ``tech_detector``,
    ``nmap_scan``, ``python_sandbox``) return raw dicts/lists that are not
    findings; those are intentionally dropped here rather than surfaced as
    noisy "info" findings. Their output is still visible in the per-run log.
    """
    if not raw:
        return []
    if _is_finding_dict(raw):
        raw = [raw]
    if not isinstance(raw, list):
        logger.debug(
            "Tool %s (%s) returned non-finding recon data; not added to findings",
            tool_name,
            agent_name,
        )
        return []

    result: list[Finding] = []
    for item in raw:
        if isinstance(item, Finding):
            item.agent = item.agent or agent_name
            item.tool = item.tool or tool_name
            result.append(item)
        elif _is_finding_dict(item):
            finding = Finding.model_validate(item)
            finding.agent = finding.agent or agent_name
            finding.tool = finding.tool or tool_name
            result.append(finding)
        else:
            logger.debug(
                "Tool %s (%s) returned a non-finding item; not added to findings",
                tool_name,
                agent_name,
            )
    return result


def run_tool_findings(
    tools: list[Callable[..., Any]],
    target: str,
    agent_name: str,
) -> list[Finding]:
    """Invoke every tool in *tools* against *target* and collect tagged findings.

    All tools are invoked (so recon tools still run and get logged), but only
    genuine vulnerability findings are returned; raw recon output is discarded
    here (not lost — it's already captured in the per-run log file).
    """
    target_url = target if target.startswith(("http://", "https://")) else f"https://{target}"
    findings: list[Finding] = []
    for tool_func in tools:
        tool_name = getattr(tool_func, "name", None) or tool_func.__class__.__name__
        dispatch_custom_event(
            "agent_update",
            {
                "phase": "step",
                "agent": agent_name,
                "tool": tool_name,
                "target": target_url,
                "status": "running",
            },
        )
        try:
            raw = tool_func.invoke(target_url)  # type: ignore[attr-defined]
        except Exception as exc:
            logger.warning("Tool %s failed for %s: %s", tool_name, target_url, exc)
            dispatch_custom_event(
                "agent_update",
                {
                    "phase": "step",
                    "agent": agent_name,
                    "tool": tool_name,
                    "target": target_url,
                    "status": "error",
                    "error": str(exc),
                },
            )
            continue
        tool_findings = _parse_tool_result(tool_name, raw, agent_name)
        dispatch_custom_event(
            "agent_update",
            {
                "phase": "step",
                "agent": agent_name,
                "tool": tool_name,
                "target": target_url,
                "status": "done",
                "findings_count": len(tool_findings),
            },
        )
        for finding in tool_findings:
            dispatch_custom_event(
                "agent_update",
                {
                    "phase": "finding",
                    "agent": agent_name,
                    "tool": tool_name,
                    "target": target_url,
                    "finding": finding.model_dump(
                        include={"id", "title", "severity", "confidence", "steps"}
                    ),
                },
            )
        findings.extend(tool_findings)
    return findings
