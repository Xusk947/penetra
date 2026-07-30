"""Common assertions for agent tests."""

from __future__ import annotations

from typing import Any


def assert_report_ok(result: dict[str, Any]) -> None:
    """Assert that an orchestrator result contains an approved report with findings."""
    assert result.get("approved") is True
    assert result.get("report")
    assert result.get("findings")


def assert_scope_denied(result: dict[str, Any]) -> None:
    """Assert that an out-of-scope target was rejected."""
    assert result.get("approved") is False or result.get("error")


def assert_research_page_ok(result: dict[str, Any]) -> None:
    """Assert that a research browser result contains readable page content."""
    assert result.get("error") is None
    assert result.get("page_title") or result.get("page_text")
