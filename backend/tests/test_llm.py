"""Tests for the OpenRouter-backed LLM factory."""

from __future__ import annotations

import pytest

from agents.common.config import Settings
from agents.common.llm import get_chat_model


def test_get_chat_model_default_openrouter_model() -> None:
    """The default OpenRouter model is ``tencent/hy3:free``."""
    settings = Settings(openrouter_api_key="dummy-key-for-tests")
    model = get_chat_model(settings)
    assert model.model_name == "tencent/hy3:free"


def test_get_chat_model_requires_api_key() -> None:
    """Creating a model without an API key must raise a clear error."""
    settings = Settings(openrouter_api_key=None)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        get_chat_model(settings)
