"""Shared constants used across agents and tools."""

from __future__ import annotations

# Default safe public target used in documentation, tests, and mock data.
DEFAULT_PUBLIC_TARGET = "example.com"
DEFAULT_RESEARCH_URL = f"https://{DEFAULT_PUBLIC_TARGET}"

# Common network/IP defaults.
LOOPBACK_IP = "127.0.0.1"
EXAMPLE_PRIVATE_IP = "10.0.0.1"
EXAMPLE_RESOLVED_IP = "93.184.216.34"

# Common HTTP/S service ports.
HTTP_PORT = 80
HTTPS_PORT = 443
SSH_PORT = 22
COMMON_MOCK_PORTS = [SSH_PORT, HTTP_PORT, HTTPS_PORT]

# Report formatting.
REPORT_TITLE = "Pentest Report"
REPORT_TITLE_MARKDOWN = f"# {REPORT_TITLE}"
EXECUTIVE_SUMMARY_TITLE = "## Executive Summary"
FINDINGS_INDEX_TITLE = "## Findings Index"
DETAILED_FINDINGS_TITLE = "## Detailed Findings"

# Severity scoring scale.
MAX_SCORE = 5
DEFAULT_SCORE = 1
INFO_SCORE = 1
LOW_SCORE = 2
MEDIUM_SCORE = 3
HIGH_SCORE = 4
CRITICAL_SCORE = 5

# Default category when a finding does not specify one.
DEFAULT_CATEGORY = "general"

# Frontdesk / research limits.
TEXT_SNIPPET_LENGTH = 500
RESEARCH_LINKS_LIMIT = 50
RESEARCH_TEXT_LIMIT = 4000

# Nmap default top-ports counts.
NMAP_TOP_PORTS_SAFE = 100
NMAP_TOP_PORTS_STANDARD = 1000

# OSINT defaults.
OSINT_TIMEOUT_SHORT = 10.0
OSINT_TIMEOUT_LONG = 15.0
OSINT_URL_LIMIT = 50
OSINT_MX_PRIORITY = 10

# Frontdesk tool output prefixes.
OSINT_SUMMARY_PREFIX = "OSINT results"
RESEARCH_SUMMARY_PREFIX = "Research summary"

# Common web paths used in mock findings and the research browser.
ADMIN_PATH = "/admin"
ABOUT_PATH = "/about"
LOGIN_PATH = "/login"
CONTACT_PATH = "/contact"

# Browser mock defaults.
MOCK_RESEARCH_PAGE_TITLE = "Mock Research Page"
