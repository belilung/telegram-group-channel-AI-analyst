"""Unit tests for the classifier — uses a stubbed ask_claude."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from tools import classifier
from tools.classifier import GroupRelevance, judge_group


@pytest.mark.asyncio
async def test_judge_group_relevant() -> None:
    fake_response = json.dumps({
        "relevant": True,
        "topic": "Hiring: Unity dev",
        "summary": "Studio seeks senior Unity developer.",
    })
    with patch("tools.classifier.ask_claude", new=AsyncMock(return_value=fake_response)):
        res = await judge_group("Шукаю Unity dev", "gamedev")
    assert res == GroupRelevance(True, "Hiring: Unity dev", "Studio seeks senior Unity developer.")


@pytest.mark.asyncio
async def test_judge_group_not_relevant() -> None:
    fake_response = '{"relevant": false, "topic": null, "summary": null}'
    with patch("tools.classifier.ask_claude", new=AsyncMock(return_value=fake_response)):
        res = await judge_group("привіт", "gamedev")
    assert res == GroupRelevance(False, None, None)


@pytest.mark.asyncio
async def test_judge_group_handles_code_fences() -> None:
    fake_response = "```json\n{\"relevant\": true, \"topic\": \"X\", \"summary\": \"y\"}\n```"
    with patch("tools.classifier.ask_claude", new=AsyncMock(return_value=fake_response)):
        res = await judge_group("text", "topic")
    assert res.relevant is True
    assert res.topic == "X"
    assert res.summary == "y"


@pytest.mark.asyncio
async def test_judge_group_retries_then_fails_closed() -> None:
    mock = AsyncMock(side_effect=["garbage no json here", "still garbage"])
    with patch("tools.classifier.ask_claude", new=mock):
        res = await judge_group("text", "topic")
    assert res == GroupRelevance(False, None, None)
    assert mock.await_count == 2


@pytest.mark.asyncio
async def test_judge_group_cli_unavailable() -> None:
    with patch(
        "tools.classifier.ask_claude",
        new=AsyncMock(side_effect=FileNotFoundError("claude CLI missing")),
    ):
        res = await judge_group("text", "topic")
    assert res == GroupRelevance(False, None, None)


def test_extract_first_json_picks_balanced_braces() -> None:
    text = "preamble {\"a\":1, \"b\":{\"c\":2}} trailing"
    assert classifier._extract_first_json(text) == "{\"a\":1, \"b\":{\"c\":2}}"


def test_extract_first_json_returns_none_when_missing() -> None:
    assert classifier._extract_first_json("no json here at all") is None
