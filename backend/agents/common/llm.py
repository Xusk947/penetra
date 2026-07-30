"""LLM factory for LangChain-based agents."""

from __future__ import annotations

from langchain_openrouter import ChatOpenRouter
from pydantic import SecretStr

from agents.common.config import Settings


def get_chat_model(settings: Settings | None = None) -> ChatOpenRouter:
    """Create a LangChain chat model backed by OpenRouter.

    The default model is ``tencent/hy3:free``. Set ``OPENROUTER_API_KEY`` and
    optionally ``OPENROUTER_MODEL`` in the environment or ``.env`` file.

    Raises:
        RuntimeError: if ``OPENROUTER_API_KEY`` is not configured.
    """
    settings = settings or Settings()
    if not settings.openrouter_api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. "
            "Add it to your .env file or environment."
        )
    return ChatOpenRouter(
        model=settings.openrouter_model,
        api_key=SecretStr(settings.openrouter_api_key),
        base_url=settings.openrouter_api_base,
        temperature=0.0,
        max_retries=2,
    )
