"""Research agent node implementations."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from agents.common.config import Settings
from agents.common.llm import get_chat_model
from agents.research.state import ResearchState
from tools.research.browser import BrowserTool

logger = logging.getLogger(__name__)


class ResearchAgent:
    """Node callables for the research browser agent."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._browser = BrowserTool(self._settings, mock=self._settings.research_mock)

    def browse(self, state: ResearchState) -> dict[str, Any]:
        """Fetch the target URL and produce a short summary."""
        if not state.target:
            return {"error": "No research target URL provided"}

        result = self._browser.fetch(state.target, mode="research")
        if result.error:
            return {"error": result.error}

        update: dict[str, Any] = {
            "page_title": result.title,
            "page_text": result.text,
            "links": result.links,
        }

        summary = self._summarize(result)
        if summary:
            update["summary"] = summary

        logger.info("Research fetched %s; title=%s", result.url, result.title)
        return update

    def _summarize(self, result: Any) -> str | None:
        """Optionally summarize the page with the LLM if an API key is configured."""
        if not self._settings.openrouter_api_key:
            return None

        try:
            model = get_chat_model(self._settings)
            prompt = (
                f"Summarize the following web page in 2-3 sentences.\n\n"
                f"URL: {result.url}\n"
                f"Title: {result.title}\n"
                f"Text: {result.text[:2000]}"
            )
            response = model.invoke(
                [
                    SystemMessage("You are a research assistant. Be concise."),
                    HumanMessage(prompt),
                ]
            )
            return response.content
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM summarization failed: %s", exc)
            return None
