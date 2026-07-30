"""Passive OSINT tool implementations."""

from __future__ import annotations

import ipaddress
import json
from typing import Any
from urllib.parse import quote

import httpx

from agents.common.config import Settings
from agents.common.constants import (
    ABOUT_PATH,
    COMMON_MOCK_PORTS,
    DEFAULT_PUBLIC_TARGET,
    EXAMPLE_RESOLVED_IP,
    HTTPS_PORT,
    HTTP_PORT,
    LOGIN_PATH,
    LOOPBACK_IP,
    OSINT_MX_PRIORITY,
    OSINT_TIMEOUT_LONG,
    OSINT_TIMEOUT_SHORT,
    OSINT_URL_LIMIT,
)
from tools.osint.base import BaseOSINTTool, OSINTResult


def _is_ip(target: str) -> bool:
    """Return True if *target* is a valid IPv4/IPv6 address."""
    try:
        ipaddress.ip_address(target)
        return True
    except ValueError:
        return False


class WhoisRDAP(BaseOSINTTool):
    """WHOIS lookup via public RDAP bootstrap (rdap.org)."""

    name = "whois_rdap"

    def _run(self, target: str) -> OSINTResult:
        kind = "ip" if _is_ip(target) else "domain"
        url = f"https://rdap.org/{kind}/{quote(target, safe='/:')}"
        response = httpx.get(url, timeout=OSINT_TIMEOUT_SHORT, follow_redirects=True)
        response.raise_for_status()
        return OSINTResult(source=self.name, target=target, data=response.json())

    def _mock_result(self, target: str) -> OSINTResult:
        return OSINTResult(
            source=self.name,
            target=target,
            data={
                "objectClassName": "domain" if not _is_ip(target) else "ip network",
                "handle": target,
                "registrar": "Mock Registrar",
                "events": [{"eventAction": "registration", "eventDate": "2020-01-01T00:00:00Z"}],
            },
        )


class ShodanInternetDB(BaseOSINTTool):
    """Shodan InternetDB passive lookup for open ports/services on an IP."""

    name = "shodan_internetdb"

    def _run(self, target: str) -> OSINTResult:
        if not _is_ip(target):
            return OSINTResult(
                source=self.name,
                target=target,
                data={},
                error="Shodan InternetDB requires an IP address, not a domain",
            )
        response = httpx.get(
            f"https://internetdb.shodan.io/{target}", timeout=OSINT_TIMEOUT_SHORT
        )
        response.raise_for_status()
        return OSINTResult(source=self.name, target=target, data=response.json())

    def _mock_result(self, target: str) -> OSINTResult:
        return OSINTResult(
            source=self.name,
            target=target,
            data={
                "cpes": [],
                "hostnames": [f"mock.{DEFAULT_PUBLIC_TARGET}"],
                "ip": target if _is_ip(target) else LOOPBACK_IP,
                "ports": COMMON_MOCK_PORTS,
                "tags": ["web"],
                "vulns": [],
            },
        )


class CensysLookup(BaseOSINTTool):
    """Censys host lookup (requires API id/secret)."""

    name = "censys"
    required_settings = ("censys_api_id", "censys_api_secret")

    def _run(self, target: str) -> OSINTResult:
        if not _is_ip(target):
            return OSINTResult(
                source=self.name,
                target=target,
                data={},
                error="Censys host lookup requires an IP address",
            )
        if not (self._settings.censys_api_id and self._settings.censys_api_secret):
            return OSINTResult(
                source=self.name,
                target=target,
                data={},
                error="CENSYS_API_ID and CENSYS_API_SECRET are not configured",
            )
        response = httpx.get(
            f"https://search.censys.io/api/v2/hosts/{target}",
            auth=(self._settings.censys_api_id, self._settings.censys_api_secret),
            timeout=OSINT_TIMEOUT_LONG,
        )
        response.raise_for_status()
        return OSINTResult(source=self.name, target=target, data=response.json())

    def _mock_result(self, target: str) -> OSINTResult:
        return OSINTResult(
            source=self.name,
            target=target,
            data={
                "code": 200,
                "status": "OK",
                "result": {
                    "ip": target,
                    "services": [
                        {"port": HTTP_PORT, "service_name": "HTTP"},
                        {"port": HTTPS_PORT, "service_name": "HTTPS"},
                    ],
                },
            },
        )


class ChaosLookup(BaseOSINTTool):
    """ProjectDiscovery Chaos passive subdomain discovery (requires API key)."""

    name = "chaos"
    required_settings = ("chaos_api_key",)

    def _run(self, target: str) -> OSINTResult:
        if _is_ip(target):
            return OSINTResult(
                source=self.name,
                target=target,
                data={},
                error="Chaos requires a domain, not an IP address",
            )
        if not self._settings.chaos_api_key:
            return OSINTResult(
                source=self.name,
                target=target,
                data={},
                error="CHAOS_API_KEY is not configured",
            )
        response = httpx.get(
            f"https://dns.projectdiscovery.io/v1/{target}/subdomains",
            headers={"Authorization": self._settings.chaos_api_key},
            timeout=OSINT_TIMEOUT_LONG,
        )
        response.raise_for_status()
        return OSINTResult(source=self.name, target=target, data=response.json())

    def _mock_result(self, target: str) -> OSINTResult:
        return OSINTResult(
            source=self.name,
            target=target,
            data={
                "domain": target,
                "subdomains": ["www", "mail", "api"],
            },
        )


class CrtShMonitor(BaseOSINTTool):
    """Certificate Transparency log monitoring via crt.sh."""

    name = "crtsh"

    def _run(self, target: str) -> OSINTResult:
        if _is_ip(target):
            return OSINTResult(
                source=self.name,
                target=target,
                data={},
                error="crt.sh requires a domain, not an IP address",
            )
        response = httpx.get(
            "https://crt.sh",
            params={"q": f"%.{target}", "output": "json"},
            timeout=OSINT_TIMEOUT_LONG,
        )
        response.raise_for_status()
        return OSINTResult(source=self.name, target=target, data={"entries": response.json()})

    def _mock_result(self, target: str) -> OSINTResult:
        return OSINTResult(
            source=self.name,
            target=target,
            data={
                "entries": [
                    {"issuer_name": "Mock CA", "name_value": f"www.{target}"},
                    {"issuer_name": "Mock CA", "name_value": f"api.{target}"},
                ]
            },
        )


class DNSDumpsterLookup(BaseOSINTTool):
    """Passive DNS via Google DNS-over-HTTPS (DoH) when no API key is set.

    The name references DNSDumpster from the methodology list; the fallback
    implementation uses public, keyless DoH endpoints for passive resolution.
    """

    name = "dnsdumpster"

    def _run(self, target: str) -> OSINTResult:
        if _is_ip(target):
            return OSINTResult(
                source=self.name,
                target=target,
                data={},
                error="DNS lookup requires a domain, not an IP address",
            )
        records: dict[str, Any] = {}
        for rtype in ("A", "AAAA", "MX", "NS", "TXT"):
            response = httpx.get(
                "https://dns.google/resolve",
                params={"name": target, "type": rtype},
                headers={"Accept": "application/dns-json"},
                timeout=OSINT_TIMEOUT_SHORT,
            )
            if response.status_code == 200:
                records[rtype] = response.json().get("Answer", [])
        return OSINTResult(source=self.name, target=target, data=records)

    def _mock_result(self, target: str) -> OSINTResult:
        return OSINTResult(
            source=self.name,
            target=target,
            data={
                "A": [{"data": EXAMPLE_RESOLVED_IP}],
                "MX": [{"data": f"{OSINT_MX_PRIORITY} mail.{DEFAULT_PUBLIC_TARGET}."}],
                "NS": [{"data": f"ns1.{DEFAULT_PUBLIC_TARGET}."}, {"data": f"ns2.{DEFAULT_PUBLIC_TARGET}."}],
            },
        )


class VirusTotalLookup(BaseOSINTTool):
    """VirusTotal domain/IP reputation lookup (requires API key)."""

    name = "virustotal"
    required_settings = ("virustotal_api_key",)

    def _run(self, target: str) -> OSINTResult:
        if not self._settings.virustotal_api_key:
            return OSINTResult(
                source=self.name,
                target=target,
                data={},
                error="VIRUSTOTAL_API_KEY is not configured",
            )
        kind = "ips" if _is_ip(target) else "domains"
        response = httpx.get(
            f"https://www.virustotal.com/api/v3/{kind}/{target}",
            headers={"x-apikey": self._settings.virustotal_api_key},
            timeout=OSINT_TIMEOUT_LONG,
        )
        response.raise_for_status()
        return OSINTResult(source=self.name, target=target, data=response.json())

    def _mock_result(self, target: str) -> OSINTResult:
        return OSINTResult(
            source=self.name,
            target=target,
            data={
                "data": {
                    "attributes": {
                        "reputation": 0,
                        "last_analysis_stats": {
                            "malicious": 0,
                            "suspicious": 0,
                            "harmless": 70,
                            "undetected": 0,
                        },
                    }
                }
            },
        )


class SecurityTrailsLookup(BaseOSINTTool):
    """SecurityTrails domain/IP lookup (requires API key)."""

    name = "securitytrails"
    required_settings = ("securitytrails_api_key",)

    def _run(self, target: str) -> OSINTResult:
        if not self._settings.securitytrails_api_key:
            return OSINTResult(
                source=self.name,
                target=target,
                data={},
                error="SECURITYTRAILS_API_KEY is not configured",
            )
        if _is_ip(target):
            response = httpx.get(
                "https://api.securitytrails.com/v1/ips/stats",
                params={"ipv4": target},
                headers={"APIKEY": self._settings.securitytrails_api_key},
                timeout=OSINT_TIMEOUT_LONG,
            )
        else:
            response = httpx.get(
                f"https://api.securitytrails.com/v1/domain/{target}",
                headers={"APIKEY": self._settings.securitytrails_api_key},
                timeout=OSINT_TIMEOUT_LONG,
            )
        response.raise_for_status()
        return OSINTResult(source=self.name, target=target, data=response.json())

    def _mock_result(self, target: str) -> OSINTResult:
        return OSINTResult(
            source=self.name,
            target=target,
            data={
                "hostname": target,
                "subdomain_count": 12,
                " Alexa_rank": 12345,
            },
        )


class IPGeolocation(BaseOSINTTool):
    """IP geolocation via ipinfo.io (free tier, optional token)."""

    name = "ip_geolocation"

    def _run(self, target: str) -> OSINTResult:
        if not _is_ip(target):
            return OSINTResult(
                source=self.name,
                target=target,
                data={},
                error="IP geolocation requires an IP address",
            )
        params: dict[str, str] = {}
        if self._settings.ipinfo_token:
            params["token"] = self._settings.ipinfo_token
        response = httpx.get(
            f"https://ipinfo.io/{target}/json",
            params=params,
            timeout=OSINT_TIMEOUT_SHORT,
        )
        response.raise_for_status()
        return OSINTResult(source=self.name, target=target, data=response.json())

    def _mock_result(self, target: str) -> OSINTResult:
        return OSINTResult(
            source=self.name,
            target=target,
            data={
                "ip": target if _is_ip(target) else LOOPBACK_IP,
                "city": "Mock City",
                "region": "Mock Region",
                "country": "US",
                "loc": "0.0000,0.0000",
                "org": "AS0 Mock ISP",
            },
        )


class WaybackMachine(BaseOSINTTool):
    """Historical URL snapshot discovery via the Wayback Machine CDX API."""

    name = "wayback_machine"

    def _run(self, target: str) -> OSINTResult:
        if _is_ip(target):
            return OSINTResult(
                source=self.name,
                target=target,
                data={},
                error="Wayback Machine requires a domain, not an IP address",
            )
        response = httpx.get(
            "https://web.archive.org/cdx/search/cdx",
            params={
                "url": f"{target}/*",
                "output": "json",
                "fl": "original",
                "collapse": "urlkey",
            },
            timeout=OSINT_TIMEOUT_LONG,
        )
        response.raise_for_status()
        try:
            urls = [row[0] for row in response.json() if row]
        except (json.JSONDecodeError, IndexError):
            urls = []
        return OSINTResult(source=self.name, target=target, data={"urls": urls[:OSINT_URL_LIMIT]})

    def _mock_result(self, target: str) -> OSINTResult:
        return OSINTResult(
            source=self.name,
            target=target,
            data={
                "urls": [
                    f"https://{target}/",
                    f"https://{target}{ABOUT_PATH}",
                    f"https://{target}{LOGIN_PATH}",
                ]
            },
        )


def get_osint_tools_summary(settings: Settings | None = None) -> str:
    """Return a markdown list of OSINT tools and their configuration status."""
    settings = settings or Settings()
    lines = []
    for tool in [
        WhoisRDAP(settings),
        ShodanInternetDB(settings),
        CensysLookup(settings),
        ChaosLookup(settings),
        CrtShMonitor(settings),
        DNSDumpsterLookup(settings),
        VirusTotalLookup(settings),
        SecurityTrailsLookup(settings),
        IPGeolocation(settings),
        WaybackMachine(settings),
    ]:
        status = tool.configuration_status()
        lines.append(f"- `{tool.name}`: {status}")
    return "\n".join(lines)


def get_osint_tools(settings: Settings | None = None) -> list[BaseOSINTTool]:
    """Return configured passive OSINT tool instances.

    In live mode tools that require an API key are skipped unless the key is
    configured. In mock mode all tools are returned so tests and demos can use
    every source.
    """
    settings = settings or Settings()
    all_tools = [
        WhoisRDAP(settings),
        ShodanInternetDB(settings),
        CensysLookup(settings),
        ChaosLookup(settings),
        CrtShMonitor(settings),
        DNSDumpsterLookup(settings),
        VirusTotalLookup(settings),
        SecurityTrailsLookup(settings),
        IPGeolocation(settings),
        WaybackMachine(settings),
    ]
    return [tool for tool in all_tools if tool.is_configured()]
