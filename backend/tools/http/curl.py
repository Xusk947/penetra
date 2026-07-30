"""Curl-style HTTP probe tool for agent use."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from langchain.tools import tool

from agents.common.config import Settings

logger = logging.getLogger(__name__)


@tool
def curl(
    url: str,
    method: str = "GET",
    headers: str | None = None,
    data: str | None = None,
    follow_redirects: bool = True,
    timeout: float = 15.0,
    verify: bool = False,
) -> dict[str, Any]:
    """Send an arbitrary HTTP request and return a structured response.

    Use this tool to probe endpoints manually, inspect headers, follow redirects
    and verify the behaviour of state-changing requests. The body is truncated
    to keep the result LLM-friendly.
    """
    settings = Settings()
    auth = None
    if settings.target_username and settings.target_password:
        auth = httpx.BasicAuth(settings.target_username, settings.target_password)

    parsed_headers: dict[str, str] = {}
    if headers:
        try:
            parsed_headers = json.loads(headers)
        except json.JSONDecodeError:
            for line in headers.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    parsed_headers[k.strip()] = v.strip()

    parsed_data: str | bytes | None = data

    try:
        with httpx.Client(auth=auth, follow_redirects=follow_redirects, timeout=timeout, verify=verify) as client:
            response = client.request(method.upper(), url, headers=parsed_headers, data=parsed_data)
    except Exception as exc:
        logger.warning("curl probe failed for %s: %s", url, exc)
        return {"error": str(exc), "url": url}

    body = response.text
    max_body = 8_000
    return {
        "url": str(response.url),
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "body": body[:max_body] + ("... (truncated)" if len(body) > max_body else ""),
        "body_length": len(body),
    }
