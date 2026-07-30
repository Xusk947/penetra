"""Environment-aware settings helpers for e2e and unit tests."""

from __future__ import annotations

import os

from dotenv import load_dotenv

from agents.common.config import Settings
from agents.common.constants import DEFAULT_PUBLIC_TARGET, DEFAULT_RESEARCH_URL, EXAMPLE_PRIVATE_IP


def default_settings() -> Settings:
    """Return a fresh ``Settings`` instance loaded from ``.env``."""
    load_dotenv(dotenv_path=".env", override=True)
    return Settings()


def allowed_scope(settings: Settings | None = None) -> list[str]:
    """Return the configured e2e scope, falling back to a safe public domain."""
    settings = settings or default_settings()
    scope = os.getenv("E2E_SCOPE")
    if scope:
        return [s.strip() for s in scope.split(",") if s.strip()]
    if settings.allowed_targets:
        return list(settings.allowed_targets)
    if settings.nmap_allowed_targets:
        return list(settings.nmap_allowed_targets)
    return [DEFAULT_PUBLIC_TARGET]


def denied_target(settings: Settings | None = None) -> str:
    """Return a target that should be denied by the scope policy."""
    settings = settings or default_settings()
    target = os.getenv("E2E_DENIED_TARGET")
    if target:
        return target
    if settings.denied_targets:
        return settings.denied_targets[0]
    return EXAMPLE_PRIVATE_IP


def research_url() -> str:
    """Return the configured research URL."""
    return os.getenv("RESEARCH_URL", DEFAULT_RESEARCH_URL)


def osint_target() -> str:
    """Return the configured OSINT target."""
    return os.getenv("OSINT_TARGET", DEFAULT_PUBLIC_TARGET)
