"""Tests for the centralized scope policy."""

from __future__ import annotations

from agents.common.config import Settings
from agents.common.scope import ScopePolicy
from tests.helpers import (
    DEFAULT_PUBLIC_TARGET,
    EVIL_DOMAIN,
    EXAMPLE_PRIVATE_IP,
    LOOPBACK_IP,
    OTHER_DOMAIN,
    PRIVATE_IP_192,
    RESEARCH_SUBDOMAIN,
    WILDCARD_PUBLIC_TARGET,
)


def test_empty_allowlist_allows_public_targets() -> None:
    """When no allowlist is set, public targets are allowed."""
    policy = ScopePolicy(Settings(allowed_targets=[]))
    assert policy.is_allowed(DEFAULT_PUBLIC_TARGET, mode="attack") is True


def test_private_ip_blocked_by_default() -> None:
    """Private IPs are blocked unless explicitly allowed."""
    policy = ScopePolicy(Settings(allowed_targets=[]))
    assert policy.is_allowed(LOOPBACK_IP, mode="attack") is False
    assert policy.is_allowed(PRIVATE_IP_192, mode="attack") is False


def test_private_ip_allowed_when_explicitly_listed() -> None:
    """A private IP can be used when it appears in the allowlist."""
    policy = ScopePolicy(Settings(allowed_targets=[LOOPBACK_IP]))
    assert policy.is_allowed(LOOPBACK_IP, mode="attack") is True


def test_denied_targets_are_blocked() -> None:
    """Targets matching the denylist are always rejected."""
    policy = ScopePolicy(
        Settings(allowed_targets=[], denied_targets=[f"*.{EVIL_DOMAIN}", EXAMPLE_PRIVATE_IP])
    )
    assert policy.is_allowed(f"foo.{EVIL_DOMAIN}", mode="attack") is False
    assert policy.is_allowed(EXAMPLE_PRIVATE_IP, mode="attack") is False


def test_wildcard_domain_allowlist() -> None:
    """Wildcard allowlists match subdomains."""
    policy = ScopePolicy(Settings(allowed_targets=[WILDCARD_PUBLIC_TARGET]))
    assert policy.is_allowed(f"www.{DEFAULT_PUBLIC_TARGET}", mode="attack") is True
    assert policy.is_allowed(DEFAULT_PUBLIC_TARGET, mode="attack") is True
    assert policy.is_allowed(OTHER_DOMAIN, mode="attack") is False


def test_research_mode_uses_separate_allowlist() -> None:
    """Research mode uses RESEARCH_ALLOWED_TARGETS instead of ALLOWED_TARGETS."""
    policy = ScopePolicy(
        Settings(
            allowed_targets=[DEFAULT_PUBLIC_TARGET],
            research_allowed_targets=[RESEARCH_SUBDOMAIN],
        )
    )
    assert policy.is_allowed(DEFAULT_PUBLIC_TARGET, mode="research") is False
    assert policy.is_allowed(RESEARCH_SUBDOMAIN, mode="research") is True


def test_filter_allowed_splits_targets() -> None:
    """filter_allowed returns allowed and denied lists."""
    policy = ScopePolicy(Settings(allowed_targets=[DEFAULT_PUBLIC_TARGET]))
    allowed, denied = policy.filter_allowed(
        [DEFAULT_PUBLIC_TARGET, EVIL_DOMAIN, LOOPBACK_IP], mode="attack"
    )
    assert allowed == [DEFAULT_PUBLIC_TARGET]
    assert denied == [EVIL_DOMAIN, LOOPBACK_IP]
