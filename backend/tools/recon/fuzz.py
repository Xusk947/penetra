"""Endpoint / path fuzzing tool for discovered web targets."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from langchain.tools import tool

from agents.common.config import Settings

logger = logging.getLogger(__name__)

DEFAULT_WORDLIST = [
    ".env", ".git/config", ".git/HEAD", "admin", "admin/", "admin/login", "api", "api/users",
    "api/v1", "api/v2", "backup", "backup.sql", "config", "config.json", "config.php.bak",
    "debug", "docs", "graphql", "login", "phpinfo.php", "register", "robots.txt", "sitemap.xml",
    "swagger", "swagger.json", "swagger.yaml", "tools", "uploads", "user", "users", "v1",
    "v2", "web.config", "wp-admin", "wp-login.php",
]


@tool
def endpoint_fuzzer(
    base_url: str,
    wordlist: str | None = None,
    extensions: str = ".html,.json,.php,.bak,.txt,.sql,.zip,.tar.gz",
    max_workers: int = 10,
) -> dict[str, Any]:
    """Brute-force common web paths and files under base_url.

    Returns a list of discovered endpoints with status code and length.
    """
    settings = Settings()
    auth = None
    if settings.target_username and settings.target_password:
        auth = httpx.BasicAuth(settings.target_username, settings.target_password)

    base = base_url.rstrip("/")
    words = [w.strip() for w in (wordlist.split(",") if wordlist else DEFAULT_WORDLIST) if w.strip()]
    exts = [e.strip() for e in extensions.split(",") if e.strip()]

    paths: list[str] = []
    for word in words:
        paths.append(f"/{word}")
        for ext in exts:
            paths.append(f"/{word}{ext}")

    found: list[dict[str, Any]] = []
    with httpx.Client(base_url=base, auth=auth, follow_redirects=True, timeout=8.0, verify=False) as client:
        from concurrent.futures import ThreadPoolExecutor

        def check(path: str) -> dict[str, Any] | None:
            try:
                resp = client.get(path)
                if resp.status_code not in (404, 410):
                    return {
                        "path": path,
                        "url": str(resp.url),
                        "status": resp.status_code,
                        "length": len(resp.content),
                    }
            except Exception as exc:
                logger.debug("fuzz error for %s: %s", path, exc)
            return None

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            for result in pool.map(check, paths):
                if result:
                    found.append(result)

    found.sort(key=lambda x: x["status"])
    return {
        "base_url": base,
        "tested": len(paths),
        "found": found,
    }
