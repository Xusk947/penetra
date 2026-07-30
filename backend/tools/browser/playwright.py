"""Playwright browser automation tool for agents."""

from __future__ import annotations

import base64
import logging
from typing import Any

from langchain.tools import tool

from agents.common.config import Settings

logger = logging.getLogger(__name__)


@tool
def playwright_browser(
    url: str,
    action: str = "visit",
    selector: str | None = None,
    value: str | None = None,
    screenshot: bool = False,
    wait_for: str | None = None,
    timeout: int = 15000,
) -> dict[str, Any]:
    """Drive a headless Chromium browser via Playwright.

    Supported actions:
    - "visit": open the URL and return page title/text/links.
    - "click": click the element matched by *selector*.
    - "fill": fill *selector* with *value*.
    - "submit": submit a form after filling.
    - "screenshot": capture a base64 PNG of the page or *selector*.

    The tool uses HTTP Basic auth from ``.env`` when ``target_username``
    and ``target_password`` are set.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        return {"error": f"Playwright is not installed: {exc}", "url": url}

    settings = Settings()
    username = settings.target_username
    password = settings.target_password

    result: dict[str, Any] = {"url": url, "action": action}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                http_credentials={"username": username, "password": password} if username and password else None,
                viewport={"width": 1280, "height": 720},
            )
            page = context.new_page()
            page.goto(url, timeout=timeout, wait_until="networkidle")

            if wait_for:
                page.wait_for_selector(wait_for, timeout=timeout)

            if action == "fill" and selector and value is not None:
                page.fill(selector, value)
            elif action == "click" and selector:
                page.click(selector)
            elif action == "submit" and selector:
                page.fill(selector, value or "")
                page.locator(selector).press("Enter")

            page.wait_for_timeout(500)

            if screenshot:
                img_bytes = page.screenshot(full_page=not selector, element=selector if selector else None)
                result["screenshot_b64"] = base64.b64encode(img_bytes).decode("ascii")

            result["title"] = page.title()
            result["text"] = page.inner_text("body")[:4000]
            result["links"] = [a.get_attribute("href") for a in page.locator("a[href]").all()]
            result["status"] = "ok"
            browser.close()
    except Exception as exc:
        logger.warning("playwright tool failed for %s: %s", url, exc)
        result["error"] = str(exc)

    return result
