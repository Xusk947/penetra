"""Lightweight browser tool for the research agent."""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx
from pydantic import BaseModel, Field

from agents.common.config import Settings
from agents.common.constants import (
    ABOUT_PATH,
    CONTACT_PATH,
    LOGIN_PATH,
    MOCK_RESEARCH_PAGE_TITLE,
    RESEARCH_LINKS_LIMIT,
    RESEARCH_TEXT_LIMIT,
)
from agents.common.scope import ScopePolicy

logger = logging.getLogger(__name__)


class BrowserResult(BaseModel):
    """Result of fetching a web page."""

    url: str
    status_code: int | None = None
    title: str | None = None
    text: str = ""
    links: list[str] = Field(default_factory=list)
    error: str | None = None


class BrowserTool:
    """Fetch a web page, extract basic metadata and visible text.

    This is a deliberately simple browser: it does not execute JavaScript.
    For JS-heavy applications, replace ``_fetch_live`` with Playwright or
    similar headless browser integration.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        mock: bool = False,
    ) -> None:
        self._settings = settings or Settings()
        self._mock = mock
        self._scope = ScopePolicy(self._settings)

    def fetch(
        self,
        url: str,
        mode: str = "research",
    ) -> BrowserResult:
        """Fetch *url* and return structured content.

        *mode* is passed to ``ScopePolicy``; use ``research`` for the
        research agent so it can use the broader ``RESEARCH_ALLOWED_TARGETS``
        list. Attack tools should use ``attack``.
        """
        if not self._scope.is_allowed(url, mode=mode):
            return BrowserResult(
                url=url,
                error=f"URL {url!r} is outside the permitted {mode} scope.",
            )

        if self._mock:
            return self._mock_fetch(url)

        try:
            return self._fetch_live(url)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Browser fetch failed for %s", url)
            return BrowserResult(url=url, error=f"Fetch failed: {exc}")

    def _fetch_live(self, url: str) -> BrowserResult:
        """Perform a real HTTP GET and parse basic page data."""
        auth = None
        if self._settings.target_username and self._settings.target_password:
            auth = httpx.BasicAuth(
                self._settings.target_username,
                self._settings.target_password,
            )

        response = httpx.get(url, follow_redirects=True, timeout=15.0, auth=auth)
        response.raise_for_status()

        html = response.text
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else None

        links = re.findall(r'href=["\'](https?://[^"\']+)["\']', html)

        text = self._html_to_text(html)

        return BrowserResult(
            url=str(response.url),
            status_code=response.status_code,
            title=title,
            text=text[:RESEARCH_TEXT_LIMIT],
            links=links[:RESEARCH_LINKS_LIMIT],
        )

    def _mock_fetch(self, url: str) -> BrowserResult:
        """Return deterministic synthetic page data."""
        logger.info("Mock browser fetch for %s", url)
        return BrowserResult(
            url=url,
            status_code=200,
            title=MOCK_RESEARCH_PAGE_TITLE,
            text=(
                f"This is a simulated page for {url}.\n"
                "It contains a login form, several navigation links, "
                "and a footer with contact information."
            ),
            links=[
                f"{url.rstrip('/')}{ABOUT_PATH}",
                f"{url.rstrip('/')}{LOGIN_PATH}",
                f"{url.rstrip('/')}{CONTACT_PATH}",
            ],
        )

    def _html_to_text(self, html: str) -> str:
        """Crudely strip HTML tags and collapse whitespace."""
        text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
