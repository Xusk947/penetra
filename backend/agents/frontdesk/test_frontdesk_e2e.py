"""End-to-end tests for the frontdesk chat agent tools."""

from __future__ import annotations

import asyncio
import os

import pytest

from agents.frontdesk.tools import run_osint, run_pentest, run_research
from tests.helpers import (
    EXPECTED_OSINT_PREFIX,
    EXPECTED_REPORT_TITLE,
    EXPECTED_RESEARCH_PREFIX,
    allowed_scope,
    default_settings,
    osint_target,
    research_url,
)


@pytest.mark.e2e
def test_e2e_frontdesk_pentest_tool() -> None:
    """Invoke the frontdesk pentest tool end-to-end."""
    result = asyncio.run(run_pentest.ainvoke({"scope": allowed_scope(default_settings())}))
    assert isinstance(result, str)
    assert EXPECTED_REPORT_TITLE in result


@pytest.mark.e2e
def test_e2e_frontdesk_osint_tool() -> None:
    """Invoke the frontdesk OSINT tool end-to-end."""
    result = asyncio.run(run_osint.ainvoke({"target": osint_target()}))
    assert isinstance(result, str)
    assert EXPECTED_OSINT_PREFIX in result


@pytest.mark.e2e
def test_e2e_frontdesk_research_tool() -> None:
    """Invoke the frontdesk research browser tool end-to-end."""
    settings = default_settings()
    if settings.research_mock and os.getenv("RESEARCH_URL") is None:
        pytest.skip("Set RESEARCH_MOCK=false and RESEARCH_URL for live research e2e.")

    result = asyncio.run(run_research.ainvoke({"url": research_url()}))
    assert isinstance(result, str)
    assert EXPECTED_RESEARCH_PREFIX in result
