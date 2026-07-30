"""Technology fingerprinting tool for web targets."""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx
from langchain.tools import tool

from agents.common.config import Settings

logger = logging.getLogger(__name__)

TECH_SIGNATURES = {
    "Werkzeug": [r"Werkzeug/[\d.]+"],
    "Flask": [r"flask", r"Flask"],
    "Django": [r"django", r"csrftoken"],
    "React": [r"react(?:\.development)?\.js", r"data-reactroot"],
    "Vue.js": [r"vue(?:\.js)?", r"__VUE__"],
    "Angular": [r"angular(?:\.min)?\.js", r"ng-app"],
    "jQuery": [r"jquery[.-]?[\d.]+"],
    "Bootstrap": [r"bootstrap[.-]?[\d.]+"],
    "PHP": [r"\.php", r"PHP/[\d.]+"],
    "Apache": [r"Apache/[\d.]+"],
    "Nginx": [r"nginx/[\d.]+"],
    "Express": [r"Express"],
    "Spring": [r"Spring"],
    "Laravel": [r"laravel_session"],
    "WordPress": [r"/wp-content/", r"/wp-includes/"],
    "Shopify": [r"myshopify", r"shopify"],
    "Gunicorn": [r"gunicorn/[\d.]+"],
    "uWSGI": [r"uWSGI"],
    "OpenResty": [r"openresty/[\d.]+"],
    "JWT": [r"eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*"],
}


@tool
def tech_detector(url: str) -> dict[str, Any]:
    """Analyze a web page and its headers to detect the technology stack."""
    settings = Settings()
    auth = None
    if settings.target_username and settings.target_password:
        auth = httpx.BasicAuth(settings.target_username, settings.target_password)

    try:
        with httpx.Client(auth=auth, follow_redirects=True, timeout=10.0, verify=False) as client:
            resp = client.get(url)
    except Exception as exc:
        logger.warning("tech detection failed for %s: %s", url, exc)
        return {"error": str(exc), "url": url}

    text = resp.text
    headers = dict(resp.headers)
    detected: set[str] = set()

    # Header-based signatures.
    header_blob = " ".join(f"{k}: {v}" for k, v in headers.items()).lower()
    if "server" in headers:
        detected.add(f"Server: {headers['server']}")
    if "x-powered-by" in headers:
        detected.add(f"X-Powered-By: {headers['x-powered-by']}")
    if "set-cookie" in headers:
        detected.add(f"Cookie names observed: {headers['set-cookie'].split(';')[0].split('=')[0]}")

    # Content-based signatures.
    for tech, patterns in TECH_SIGNATURES.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE) or re.search(pattern, header_blob, re.IGNORECASE):
                detected.add(tech)
                break

    # Extract frameworks from script src and comments.
    scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', text, re.IGNORECASE)
    for src in scripts:
        for tech, patterns in TECH_SIGNATURES.items():
            if any(re.search(p, src, re.IGNORECASE) for p in patterns):
                detected.add(tech)

    return {
        "url": str(resp.url),
        "status_code": resp.status_code,
        "detected_technologies": sorted(detected),
        "scripts": scripts[:20],
        "headers": headers,
    }
