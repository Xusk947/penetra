"""Black-box web vulnerability tools exposed to the pentest agents.

Each tool is a thin wrapper around a specific ``WebScanner`` check. The agents
import the tool lists and invoke them, rather than letting a single monolithic
scanner drive the entire assessment.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Callable

from langchain.tools import tool

from agents.common.config import Settings
from agents.common.models import Finding
from tools.browser.playwright import playwright_browser
from tools.http.curl import curl
from tools.recon.fuzz import endpoint_fuzzer
from tools.recon.nmap import nmap_scan
from tools.recon.tech import tech_detector
from tools.sandbox.python import python_sandbox
from tools.vuln.web_scanner import WebScanner


@lru_cache
def _get_scanner() -> WebScanner:
    """Return a shared WebScanner instance for the current runtime settings."""
    return WebScanner(Settings())


def _scanner_tool(name: str, method: str, description: str) -> Callable[..., Any]:
    """Create a LangChain tool that invokes one ``WebScanner`` check."""

    @tool(name, description=description)
    def _run(target: str) -> list[dict[str, Any]]:
        """Run the scanner check and return serialized findings."""
        scanner = _get_scanner()
        findings: list[Finding] = getattr(scanner, method)()
        return [f.model_dump() for f in findings]

    return _run


# ---------------------------------------------------------------------------
# Client-side tools (used by the client-side security agent)
# ---------------------------------------------------------------------------
sql_injection_login_test = _scanner_tool(
    "sql_injection_login_test",
    "check_sqli_login_bypass",
    "Test the /login form for SQL injection authentication bypass.",
)

sql_injection_search_test = _scanner_tool(
    "sql_injection_search_test",
    "check_sqli_search_union",
    "Test the /doctors search for UNION-based SQL injection and data extraction.",
)

reflected_xss_test = _scanner_tool(
    "reflected_xss_test",
    "check_xss_reflected",
    "Test the /doctors search parameter for reflected XSS.",
)

stored_xss_test = _scanner_tool(
    "stored_xss_test",
    "check_xss_stored",
    "Register a patient with an XSS payload in full_name and check for stored XSS.",
)

idor_test = _scanner_tool(
    "idor_test",
    "check_idor",
    "Check /cabinet/{id} endpoints for Insecure Direct Object Reference.",
)

csrf_test = _scanner_tool(
    "csrf_test",
    "check_csrf",
    "Inspect POST forms for anti-CSRF tokens.",
)

cookie_flags_test = _scanner_tool(
    "cookie_flags_test",
    "check_cookie_flags",
    "Check the session cookie for HttpOnly, Secure and SameSite flags.",
)

rate_limit_test = _scanner_tool(
    "rate_limit_test",
    "check_rate_limit",
    "Send repeated failed login requests to verify rate limiting.",
)

CLIENT_TOOLS = [
    sql_injection_login_test,
    sql_injection_search_test,
    reflected_xss_test,
    stored_xss_test,
    idor_test,
    csrf_test,
    cookie_flags_test,
    rate_limit_test,
    playwright_browser,
]

# ---------------------------------------------------------------------------
# Server-side tools (used by the server-side security agent)
# ---------------------------------------------------------------------------
exposed_backup_test = _scanner_tool(
    "exposed_backup_test",
    "check_exposed_backup",
    "Check whether /admin/backup is accessible and returns a database file.",
)

exposed_api_patients_test = _scanner_tool(
    "exposed_api_patients_test",
    "check_exposed_api_patients",
    "Check whether /api/patients is accessible without authentication.",
)

exposed_secret_file_test = _scanner_tool(
    "exposed_secret_file_test",
    "check_exposed_secret_file",
    "Check for exposed /static/config.py.bak secrets file.",
)

debug_rce_test = _scanner_tool(
    "debug_rce_test",
    "check_debug_rce",
    "Detect Werkzeug interactive debugger / unhandled exception RCE at /tools/bmi.",
)

weak_credentials_test = _scanner_tool(
    "weak_credentials_test",
    "check_weak_credentials",
    "Test the login/admin form for weak/default credentials.",
)

path_traversal_test = _scanner_tool(
    "path_traversal_test",
    "check_path_traversal",
    "Test /admin/download for path traversal with an admin session.",
)

command_injection_test = _scanner_tool(
    "command_injection_test",
    "check_command_injection",
    "Test /admin/ping for command injection with an admin session.",
)

SERVER_TOOLS = [
    exposed_backup_test,
    exposed_api_patients_test,
    exposed_secret_file_test,
    debug_rce_test,
    weak_credentials_test,
    path_traversal_test,
    command_injection_test,
    endpoint_fuzzer,
    tech_detector,
]

# ---------------------------------------------------------------------------
# IoT/Infrastructure tools (used by the IoT/infrastructure agent)
# ---------------------------------------------------------------------------
default_admin_credentials_test = _scanner_tool(
    "default_admin_credentials_test",
    "check_default_admin_creds_iot",
    "Check management/admin interfaces for default/weak credentials.",
)

IOT_TOOLS = [
    default_admin_credentials_test,
    nmap_scan,
]

# ---------------------------------------------------------------------------
# General-purpose tools available to every domain agent
# ---------------------------------------------------------------------------
GENERAL_TOOLS = [
    curl,
    python_sandbox,
]


def client_tools() -> list[Callable[..., Any]]:
    """Return the list of client-side security tools."""
    return list(GENERAL_TOOLS + CLIENT_TOOLS)


def server_tools() -> list[Callable[..., Any]]:
    """Return the list of server-side security tools."""
    return list(GENERAL_TOOLS + SERVER_TOOLS)


def iot_tools() -> list[Callable[..., Any]]:
    """Return the list of IoT/infrastructure security tools."""
    return list(GENERAL_TOOLS + IOT_TOOLS)
