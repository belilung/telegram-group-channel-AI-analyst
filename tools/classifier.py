"""Claude-CLI-backed classifier for group/channel message relevance.

Single entrypoint: `judge_group(text, topic_hint)` → `GroupRelevance`.

All LLM calls go through `tools.claude_chat.ask_claude` which shells out to
`claude -p`. No Anthropic API key needed — Claude Pro subscription only.

System prompt: `system_prompts/group_relevance_filter.md`.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.config import PROJECT_ROOT, get_settings
from tools.claude_chat import ask_claude

logger = logging.getLogger(__name__)

MAX_TEXT_CHARS = 4000
RETRY_SUFFIX = "\n\nReturn ONLY valid JSON, no prose, no fences."

PROMPT_GROUP = PROJECT_ROOT / "system_prompts" / "group_relevance_filter.md"


@dataclass(frozen=True)
class GroupRelevance:
    relevant: bool
    topic: Optional[str]
    summary: Optional[str]


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


@lru_cache(maxsize=4)
def _load_prompt(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _strip_fences(text: str) -> str:
    return _FENCE_RE.sub("", text).strip()


def _extract_first_json(text: str) -> Optional[str]:
    text = _strip_fences(text)
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _truncate(text: Optional[str]) -> str:
    if not text:
        return ""
    return text[:MAX_TEXT_CHARS]


async def _call_claude(payload: dict, system_prompt: str) -> Optional[dict]:
    settings = get_settings()
    user_message = json.dumps(payload, ensure_ascii=False)
    try:
        raw = await ask_claude(
            user_message=user_message,
            system_prompt=system_prompt,
            model=settings.claude_model,
        )
    except (FileNotFoundError, RuntimeError) as exc:
        logger.error("claude CLI failed: %s", exc)
        return None

    candidate = _extract_first_json(raw)
    if candidate is not None:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            logger.warning("classifier.parse_failed first-pass len=%d", len(raw))

    try:
        raw2 = await ask_claude(
            user_message=user_message + RETRY_SUFFIX,
            system_prompt=system_prompt,
            model=settings.claude_model,
        )
    except (FileNotFoundError, RuntimeError) as exc:
        logger.error("claude CLI retry failed: %s", exc)
        return None

    candidate2 = _extract_first_json(raw2)
    if candidate2 is None:
        logger.error("classifier.parse_failed no_json_retry len=%d", len(raw2))
        return None
    try:
        return json.loads(candidate2)
    except json.JSONDecodeError as exc:
        logger.error("classifier.parse_failed json_decode_retry: %s", exc)
        return None


async def judge_group(text: str, topic_hint: str) -> GroupRelevance:
    """Decide whether a group/channel message is relevant to `topic_hint`.

    Fails-closed (relevant=False) on any LLM / parser error.
    """
    payload = {"message": _truncate(text), "topic_hint": topic_hint or ""}
    system_prompt = _load_prompt(str(PROMPT_GROUP))
    parsed = await _call_claude(payload, system_prompt)
    if not parsed:
        return GroupRelevance(False, None, None)

    relevant = bool(parsed.get("relevant", False))
    topic = parsed.get("topic")
    summary = parsed.get("summary")
    topic = (str(topic).strip()[:60] or None) if topic else None
    summary = (str(summary).strip()[:200] or None) if summary else None
    if not relevant:
        return GroupRelevance(False, None, None)
    return GroupRelevance(True, topic, summary)


async def _cli_main(args: list[str]) -> int:
    """Smoke test from the shell:
        python -m tools.classifier "<text>" --hint=3d
    """
    import sys

    if not args:
        print("Usage: python -m tools.classifier '<text>' [--hint=<topic>]",
              file=sys.stderr)
        return 2
    text = args[0]
    topic_hint = ""
    for a in args[1:]:
        if a.startswith("--hint="):
            topic_hint = a.split("=", 1)[1]
    res = await judge_group(text, topic_hint)
    print(json.dumps(
        {"relevant": res.relevant, "topic": res.topic, "summary": res.summary},
        ensure_ascii=False, indent=2,
    ))
    return 0


if __name__ == "__main__":
    import asyncio
    import sys

    raise SystemExit(asyncio.run(_cli_main(sys.argv[1:])))
