"""Tests for report language detection and findings localization."""

# ruff: noqa: RUF001  (Cyrillic test strings are intentional)

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage

from agents.frontdesk.tools import (
    _detect_user_language,
    _resolve_report_language,
)
from agents.reporter.render import localize_findings


@dataclass
class FakeRuntime:
    """Minimal stand-in for langchain ToolRuntime."""

    state: dict[str, Any] = field(default_factory=dict)


def test_detect_language_cyrillic() -> None:
    runtime = FakeRuntime(state={"messages": [HumanMessage(content="проверь систему")]})
    assert _detect_user_language(runtime) == "ru"


def test_detect_language_english_returns_none() -> None:
    runtime = FakeRuntime(state={"messages": [HumanMessage(content="check the system")]})
    assert _detect_user_language(runtime) is None


def test_detect_language_uses_last_human_message() -> None:
    runtime = FakeRuntime(
        state={
            "messages": [
                HumanMessage(content="check the system"),
                AIMessage(content="running scan"),
                HumanMessage(content="проверь бекенд"),
            ]
        }
    )
    assert _detect_user_language(runtime) == "ru"


def test_detect_language_block_content() -> None:
    runtime = FakeRuntime(
        state={"messages": [HumanMessage(content=[{"type": "text", "text": "поищи доступы"}])]}
    )
    assert _detect_user_language(runtime) == "ru"


def test_detect_language_no_runtime() -> None:
    assert _detect_user_language(None) is None


def test_resolve_report_language_auto_detects() -> None:
    runtime = FakeRuntime(state={"messages": [HumanMessage(content="проверь систему")]})
    assert _resolve_report_language("auto", runtime) == "ru"


def test_resolve_report_language_explicit_wins() -> None:
    runtime = FakeRuntime(state={"messages": [HumanMessage(content="проверь систему")]})
    assert _resolve_report_language("es", runtime) == "es"


def test_resolve_report_language_auto_no_match_falls_back_en() -> None:
    runtime = FakeRuntime(state={"messages": [HumanMessage(content="scan it")]})
    assert _resolve_report_language("auto", runtime) == "en"


def _findings() -> list[dict[str, Any]]:
    return [
        {
            "id": "VULN-AAA",
            "title": "Exposed secrets",
            "description": "Config file is public.",
            "remediation": "Remove it from web root.",
            "steps": ["GET /static/config.py.bak", "Observe secrets"],
            "severity": "high",
        },
        {
            "id": "VULN-BBB",
            "title": "IDOR",
            "description": "Object reference is guessable.",
            "remediation": "Enforce authorization.",
            "steps": [],
            "severity": "medium",
        },
    ]


def _mock_model(payload: Any) -> MagicMock:
    model = MagicMock()
    response = MagicMock()
    import json

    response.content = f"```json\n{json.dumps(payload, ensure_ascii=False)}\n```"
    model.invoke.return_value = response
    return model


def test_localize_findings_en_passthrough() -> None:
    findings = _findings()
    assert localize_findings(findings, "en") is findings


def test_localize_findings_merges_translation() -> None:
    translated = [
        {
            "id": "VULN-AAA",
            "title": "Раскрытые секреты",
            "description": "Конфиг общедоступен.",
            "remediation": "Уберите его из веб-корня.",
            "steps": ["GET /static/config.py.bak", "Секреты видны"],
        },
        {
            "id": "VULN-BBB",
            "title": "IDOR",
            "description": "Ссылка на объект угадывается.",
            "remediation": "Проверяйте авторизацию.",
            "steps": [],
        },
    ]
    with patch("agents.reporter.render.get_chat_model", return_value=_mock_model(translated)):
        result = localize_findings(_findings(), "ru")
    assert result[0]["title"] == "Раскрытые секреты"
    assert result[0]["steps"] == ["GET /static/config.py.bak", "Секреты видны"]
    assert result[0]["severity"] == "high"  # untouched fields preserved
    assert result[1]["remediation"] == "Проверяйте авторизацию."


def test_localize_findings_failure_returns_originals() -> None:
    model = MagicMock()
    model.invoke.side_effect = RuntimeError("boom")
    findings = _findings()
    with patch("agents.reporter.render.get_chat_model", return_value=model):
        assert localize_findings(findings, "ru") == findings


def test_localize_findings_shape_mismatch_returns_originals() -> None:
    findings = _findings()
    with patch(
        "agents.reporter.render.get_chat_model",
        return_value=_mock_model([{"id": "VULN-AAA", "title": "x"}]),
    ):
        assert localize_findings(findings, "ru") == findings
