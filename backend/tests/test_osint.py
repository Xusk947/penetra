"""Tests for the passive OSINT agent."""

from __future__ import annotations

from agents.common.config import Settings
from agents.osint.graph import build_graph
from agents.osint.state import OSINTState
from tests.helpers import DEFAULT_PUBLIC_TARGET, EXPECTED_OSINT_SOURCE_COUNT
from tools.osint.tools import IPGeolocation, ShodanInternetDB, get_osint_tools


def test_osint_agent_collects_mocked_results() -> None:
    """The OSINT agent should return a result for every configured source."""
    settings = Settings(osint_mock=True)
    graph = build_graph(settings)

    final = graph.invoke(OSINTState(target=DEFAULT_PUBLIC_TARGET))

    assert final["target"] == DEFAULT_PUBLIC_TARGET
    assert len(final["results"]) == EXPECTED_OSINT_SOURCE_COUNT
    assert "whois_rdap" in final["results"]
    assert "shodan_internetdb" in final["results"]
    assert "crtsh" in final["results"]
    assert final.get("error") is None


def test_ip_only_tools_reject_domain() -> None:
    """Tools that require an IP address should return a clear error for a domain."""
    settings = Settings(osint_mock=False)

    shodan = ShodanInternetDB(settings)
    result = shodan.run(DEFAULT_PUBLIC_TARGET)
    assert result.error is not None
    assert "IP address" in result.error

    geo = IPGeolocation(settings)
    result = geo.run(DEFAULT_PUBLIC_TARGET)
    assert result.error is not None
    assert "IP address" in result.error


def test_get_osint_tools_filters_unconfigured_in_live_mode() -> None:
    """In live mode, key-only tools are hidden when API keys are missing."""
    settings = Settings(osint_mock=False)
    tools = get_osint_tools(settings)

    names = {tool.name for tool in tools}
    # These sources do not require an API key
    assert "whois_rdap" in names
    assert "shodan_internetdb" in names
    assert "crtsh" in names
    # These require API keys and should be filtered out
    assert "censys" not in names
    assert "virustotal" not in names


def test_get_osint_tools_returns_all_sources() -> None:
    """The tool factory should return all 10 OSINT sources."""
    settings = Settings(osint_mock=True)
    tools = get_osint_tools(settings)

    names = {tool.name for tool in tools}
    expected = {
        "whois_rdap",
        "shodan_internetdb",
        "censys",
        "chaos",
        "crtsh",
        "dnsdumpster",
        "virustotal",
        "securitytrails",
        "ip_geolocation",
        "wayback_machine",
    }
    assert names == expected
