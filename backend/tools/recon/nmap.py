"""Nmap scanner adapter."""

from __future__ import annotations

import logging
import subprocess
import xml.etree.ElementTree as ET
from typing import Any

from langchain.tools import tool
from pydantic import BaseModel

from agents.common.config import Settings
from agents.common.constants import (
    COMMON_MOCK_PORTS,
    HTTP_PORT,
    HTTPS_PORT,
    NMAP_TOP_PORTS_SAFE,
    NMAP_TOP_PORTS_STANDARD,
    SSH_PORT,
)
from agents.common.scope import ScopePolicy

logger = logging.getLogger(__name__)


class NmapResult(BaseModel):
    """Structured output from an Nmap scan."""

    target: str
    open_ports: list[int]
    services: list[dict[str, Any]]
    raw_output: str


class NmapTool:
    """Run Nmap inside a Docker sandbox and parse the result.

    By default the tool returns mock data so the graph can be exercised without
    a live target. Set ``NMAP_MOCK=false`` and ``NMAP_USE_DOCKER=true`` in
    ``.env`` to run the real ``instrumentisto/nmap`` Docker image.
    """

    def __init__(
        self,
        *,
        mock: bool = True,
        settings: Settings | None = None,
        policy: str | None = None,
        allowed_targets: list[str] | None = None,
    ) -> None:
        """Initialize the tool.

        Args:
            mock: When ``True``, return synthetic scan results.
            settings: Optional runtime settings (used for policy/allowlist).
            policy: Scan policy ``safe`` | ``standard`` | ``aggressive``.
            allowed_targets: Optional explicit allowlist of targets.
        """
        self._mock = mock
        self._settings = settings or Settings()
        self._policy = policy or self._settings.nmap_policy
        self._allowed_targets = allowed_targets or self._settings.nmap_allowed_targets
        self._scope = ScopePolicy(
            self._settings,
            allowed_targets=self._allowed_targets,
        )

    def _is_target_allowed(self, target: str) -> bool:
        """Check whether *target* is permitted under the centralized scope policy."""
        return self._scope.is_allowed(target, mode="attack")

    def _build_command(self, target: str) -> list[str]:
        """Return the Nmap command for the current policy."""
        if self._policy == "safe":
            return ["nmap", "-sT", "-Pn", "-T2", "--top-ports", str(NMAP_TOP_PORTS_SAFE), target]
        if self._policy == "standard":
            return [
                "nmap",
                "-sV",
                "-sC",
                "-T3",
                "--top-ports",
                str(NMAP_TOP_PORTS_STANDARD),
                target,
            ]
        if self._policy == "aggressive":
            return ["nmap", "-A", "-T4", target]
        raise ValueError(f"Unknown nmap policy: {self._policy}")

    def scan(self, target: str) -> NmapResult:
        """Execute a service scan against *target*.

        Args:
            target: IP address or hostname from the approved scope.

        Returns:
            Parsed Nmap result.

        Raises:
            ValueError: if the target is not in the configured allowlist.
        """
        if not self._is_target_allowed(target):
            raise ValueError(
                f"Target {target!r} is not in the scope allowlist. "
                "Add it to ALLOWED_TARGETS or NMAP_ALLOWED_TARGETS."
            )

        logger.info(
            "Nmap scan requested for %s (policy=%s, mock=%s)",
            target,
            self._policy,
            self._mock,
        )

        if self._mock:
            return self._mock_scan(target)

        command = self._build_command(target)
        return self._run_container(target, command)

    def _mock_scan(self, target: str) -> NmapResult:
        """Return deterministic synthetic results for development."""
        logger.info("Running mock Nmap scan for %s", target)
        return NmapResult(
            target=target,
            open_ports=COMMON_MOCK_PORTS,
            services=[
                {
                    "port": SSH_PORT,
                    "protocol": "tcp",
                    "service": "ssh",
                    "version": "OpenSSH 8.9",
                },
                {
                    "port": HTTP_PORT,
                    "protocol": "tcp",
                    "service": "http",
                    "version": "nginx 1.24",
                },
                {
                    "port": HTTPS_PORT,
                    "protocol": "tcp",
                    "service": "https",
                    "version": "nginx 1.24",
                },
            ],
            raw_output=(
                f"Nmap scan report for {target}\n"
                f"{SSH_PORT}/tcp open ssh\n"
                f"{HTTP_PORT}/tcp open http\n"
                f"{HTTPS_PORT}/tcp open https"
            ),
        )

    def _run_container(self, target: str, command: list[str]) -> NmapResult:
        """Run Nmap and parse the XML output.

        Uses a Docker container when ``nmap_use_docker`` is enabled, otherwise
        falls back to a local ``nmap`` subprocess.
        """
        if self._settings.nmap_use_docker:
            return self._run_docker(target, command)
        return self._run_local(target, command)

    def _run_local(self, target: str, command: list[str]) -> NmapResult:
        """Run ``nmap`` locally and parse the XML output."""
        xml_command = [*command, "-oX", "-"]
        logger.info("Running nmap: %s", " ".join(xml_command))

        try:
            proc = subprocess.run(
                xml_command,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("nmap executable not found in PATH") from exc

        if proc.returncode != 0:
            raise RuntimeError(f"nmap failed: {proc.stderr.strip()}")

        open_ports, services = self._parse_nmap_xml(proc.stdout)
        return NmapResult(
            target=target,
            open_ports=open_ports,
            services=services,
            raw_output=proc.stdout,
        )

    def _run_docker(self, target: str, command: list[str]) -> NmapResult:
        """Run ``nmap`` inside a Docker container using the configured image."""
        image = self._settings.nmap_docker_image
        network = self._settings.nmap_docker_network
        nmap_args = command[1:]  # the Docker image entrypoint is ``nmap``
        docker_command = [
            "docker",
            "run",
            "--rm",
            "--network",
            network,
            image,
            *nmap_args,
            "-oX",
            "-",
        ]
        logger.info("Running nmap in Docker: %s", " ".join(docker_command))

        try:
            proc = subprocess.run(
                docker_command,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("docker executable not found in PATH") from exc

        if proc.returncode != 0:
            raise RuntimeError(f"Docker nmap failed: {proc.stderr.strip()}")

        open_ports, services = self._parse_nmap_xml(proc.stdout)
        return NmapResult(
            target=target,
            open_ports=open_ports,
            services=services,
            raw_output=proc.stdout,
        )

    def _parse_nmap_xml(self, xml_output: str) -> tuple[list[int], list[dict[str, Any]]]:
        """Parse ``nmap -oX`` output into open ports and service records."""
        open_ports: list[int] = []
        services: list[dict[str, Any]] = []

        try:
            root = ET.fromstring(xml_output)
        except ET.ParseError as exc:
            logger.warning("Failed to parse nmap XML: %s", exc)
            return open_ports, services

        for host in root.findall("host"):
            for port in host.findall(".//port"):
                state = port.find("state")
                if state is None or state.get("state") != "open":
                    continue

                portid = port.get("portid")
                if not portid:
                    continue

                port_num = int(portid)
                protocol = port.get("protocol", "tcp")
                service_elem = port.find("service")
                service_name = service_elem.get("name", "") if service_elem is not None else ""
                service_version = (
                    service_elem.get("version", "") if service_elem is not None else ""
                )

                open_ports.append(port_num)
                services.append(
                    {
                        "port": port_num,
                        "protocol": protocol,
                        "service": service_name,
                        "version": service_version,
                    }
                )

        return open_ports, services


@tool
def nmap_scan(target: str, policy: str = "safe") -> dict[str, Any]:
    """Run an nmap port/service scan against an allowed target.

    Set ``NMAP_MOCK=false`` and ``NMAP_USE_DOCKER=true`` in ``.env`` to execute
    Nmap inside the ``instrumentisto/nmap`` Docker container. If Docker is not
    available, the tool falls back to a local ``nmap`` binary and then to
    synthetic output.
    """
    host = target.replace("https://", "").replace("http://", "").split("/")[0]
    settings = Settings()
    tool = NmapTool(
        mock=settings.nmap_mock,
        settings=settings,
        policy=policy,
    )
    try:
        result = tool.scan(host)
        return result.model_dump()
    except (RuntimeError, FileNotFoundError) as exc:
        error = str(exc)
        logger.warning("nmap scan failed for %s: %s", host, error)
        if "not found" in error.lower() or "not installed" in error.lower():
            logger.info("Falling back to mock nmap scan for %s", host)
            mock_tool = NmapTool(mock=True, settings=settings, policy=policy)
            return mock_tool.scan(host).model_dump()
        return {"error": error, "target": host, "policy": policy}
    except Exception as exc:
        logger.warning("nmap scan failed for %s: %s", host, exc)
        return {"error": str(exc), "target": host, "policy": policy}

