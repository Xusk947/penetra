"""Vulnerability analysis agent node implementations."""

from __future__ import annotations

import logging
from typing import Any

from agents.common.models import Finding
from agents.vuln.state import VulnState

logger = logging.getLogger(__name__)


class VulnAgent:
    """Node callables for the vulnerability analysis agent."""

    def analyze(self, state: VulnState) -> dict[str, Any]:
        """Analyze discovered services for known vulnerability patterns."""
        findings: list[Finding] = []

        for svc in state.services:
            svc_name = svc.service.lower()
            if svc_name == "http" and svc.port == 80:
                findings.append(
                    Finding(
                        title="Plain-text HTTP service detected",
                        severity="low",
                        confidence="certain",
                        description=(
                            f"Target exposes HTTP on port {svc.port}"
                            " without redirect to HTTPS."
                        ),
                        cwe="CWE-319",
                        remediation="Redirect HTTP traffic to HTTPS or disable the service.",
                        agent="vuln",
                        tool="service_analysis",
                        steps=[f"Observe open port {svc.port}/tcp running {svc.service}"],
                    )
                )

            if svc_name == "ssh":
                findings.append(
                    Finding(
                        title="SSH service exposed",
                        severity="info",
                        confidence="certain",
                        description=f"SSH service running on port {svc.port}.",
                        cwe=None,
                        remediation=None,
                        agent="vuln",
                        tool="service_analysis",
                        steps=[f"Observe open port {svc.port}/tcp running {svc.service}"],
                    )
                )

        logger.info("Generated %d findings", len(findings))
        return {"findings": findings}
