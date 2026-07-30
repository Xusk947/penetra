"""Centralized scope policy for all attack and research agents."""

from __future__ import annotations

import ipaddress
from fnmatch import fnmatch
from urllib.parse import urlparse

from agents.common.config import Settings


class ScopePolicy:
    """Enforce target allowlists/denylists for attack and research activity.

    *Attack mode* (used by client/server/iot agents and scanner tools):
      - target must match ``allowed_targets``
      - target must not match ``denied_targets``
      - private/reserved IPs are blocked unless explicitly allowed

    *Research mode* (used by the research browser):
      - target must match ``research_allowed_targets`` (if configured)
      - target must not match ``denied_targets``
      - private/reserved IPs are still blocked unless explicitly allowed
    """

    _RESERVED_NETWORKS = (
        "0.0.0.0/8",
        "10.0.0.0/8",
        "100.64.0.0/10",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.0.0.0/24",
        "192.0.2.0/24",
        "192.168.0.0/16",
        "198.18.0.0/15",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "224.0.0.0/4",
        "240.0.0.0/4",
        "::1/128",
        "fc00::/7",
        "fe80::/10",
    )

    def __init__(
        self,
        settings: Settings | None = None,
        allowed_targets: list[str] | None = None,
        denied_targets: list[str] | None = None,
        research_allowed_targets: list[str] | None = None,
    ) -> None:
        """Load policy from settings, with optional per-instance overrides."""
        self._settings = settings or Settings()
        self._allowed_targets = allowed_targets
        self._denied_targets = denied_targets
        self._research_allowed_targets = research_allowed_targets
        self._reserved = [ipaddress.ip_network(n) for n in self._RESERVED_NETWORKS]

    def _normalize_target(self, target: str) -> str:
        """Strip URL scheme and path, leaving only host/IP for matching."""
        if target.startswith(("http://", "https://")):
            parsed = urlparse(target)
            return parsed.hostname or parsed.netloc
        if "/" in target:
            return target.split("/", 1)[0]
        return target

    def _is_private_or_reserved(self, target: str) -> bool:
        """Return True if *target* is a private/reserved IP address."""
        host = self._normalize_target(target)
        try:
            addr = ipaddress.ip_address(host)
        except ValueError:
            return False
        return any(addr in net for net in self._reserved)

    def _matches(self, target: str, patterns: list[str]) -> bool:
        """Return True if *target* matches any pattern (exact, wildcard, or suffix)."""
        for pattern in patterns:
            pattern = pattern.strip()
            if not pattern:
                continue
            if fnmatch(target, pattern):
                return True
            if target == pattern:
                return True
            if pattern.startswith("*.") and target.endswith(pattern.lstrip("*.")):
                return True
            if target == pattern.lstrip("*."):
                return True
        return False

    def _denylist(self) -> list[str]:
        """Return the active denylist (override or settings)."""
        return list(self._denied_targets if self._denied_targets is not None else self._settings.denied_targets)

    def _allowlist_for_mode(self, mode: str) -> list[str]:
        """Return the active allowlist for the given mode."""
        if mode == "research":
            return list(
                self._research_allowed_targets
                if self._research_allowed_targets is not None
                else self._settings.research_allowed_targets
            )
        if mode == "attack":
            return list(
                self._allowed_targets
                if self._allowed_targets is not None
                else self._settings.allowed_targets
            )
        return []

    def is_allowed(self, target: str, mode: str = "attack") -> bool:
        """Check whether *target* is permitted for *mode*."""
        host = self._normalize_target(target)

        if self._matches(host, self._denylist()):
            return False

        if self._settings.block_private_ips and self._is_private_or_reserved(host):
            allowed = self._allowlist_for_mode(mode)
            if not self._matches(host, allowed):
                return False

        allowlist = self._allowlist_for_mode(mode)
        if allowlist and not self._matches(host, allowlist):
            return False

        return True

    def filter_allowed(
        self,
        targets: list[str],
        mode: str = "attack",
    ) -> tuple[list[str], list[str]]:
        """Split *targets* into (allowed, denied) for *mode*."""
        allowed: list[str] = []
        denied: list[str] = []
        for target in targets:
            if self.is_allowed(target, mode=mode):
                allowed.append(target)
            else:
                denied.append(target)
        return allowed, denied

    def validate(self, targets: list[str], mode: str = "attack") -> tuple[bool, str]:
        """Validate that at least one *target* is allowed for *mode*.

        Returns a tuple of (approved, error_message).
        """
        if not targets:
            return False, "Empty scope: no targets provided"

        allowed, denied = self.filter_allowed(targets, mode=mode)
        if not allowed:
            return False, (
                f"All targets are outside the approved scope for {mode!r}: {denied}. "
                "Add them to ALLOWED_TARGETS (attack) or RESEARCH_ALLOWED_TARGETS (research)."
            )

        return True, ""
