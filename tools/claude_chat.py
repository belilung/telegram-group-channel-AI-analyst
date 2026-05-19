"""Send a prompt to Claude via the `claude` CLI and return the response.

Usage:
    from tools.claude_chat import ask_claude
    response = await ask_claude("Hello", system_prompt="...")

Requires the `claude` CLI to be installed and authenticated
(https://claude.ai/code) — Claude Pro subscription, no ANTHROPIC_API_KEY.
"""

from __future__ import annotations

import asyncio
import os
import shutil
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "claude-haiku-4-5"


def _format_prompt(history: list[dict], user_message: str) -> str:
    lines: list[str] = []
    for turn in history:
        role = str(turn.get("role", "user")).capitalize()
        content = turn.get("content", "")
        lines.append(f"{role}: {content}")
    lines.append(f"User: {user_message}")
    return "\n\n".join(lines)


async def ask_claude(
    user_message: str,
    system_prompt: str = "",
    model: Optional[str] = None,
    history: Optional[list[dict]] = None,
    timeout: float = 60.0,
) -> str:
    """Send a message to Claude via the `claude` CLI and return the response.

    Raises:
        FileNotFoundError: if the `claude` CLI is not installed in PATH.
        RuntimeError: if the CLI exits non-zero or times out.
    """
    cli_path = shutil.which("claude")
    if cli_path is None:
        raise FileNotFoundError(
            "`claude` CLI not found in PATH. Install it from "
            "https://claude.ai/code and run it once to authenticate."
        )

    selected_model = model or os.getenv("CLAUDE_MODEL", DEFAULT_MODEL)
    prompt = _format_prompt(history or [], user_message)

    args: list[str] = [
        cli_path,
        "-p",
        "--model", selected_model,
        "--output-format", "text",
    ]
    if system_prompt:
        args.extend(["--append-system-prompt", system_prompt])

    proc = await asyncio.create_subprocess_exec(
        *args,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(prompt.encode("utf-8")),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            pass
        raise RuntimeError(f"claude CLI timed out after {timeout:.0f}s")

    if proc.returncode != 0:
        err = stderr.decode("utf-8", errors="replace").strip()[:200]
        raise RuntimeError(
            f"claude CLI failed (exit {proc.returncode}): {err or '<no stderr>'}"
        )

    return stdout.decode("utf-8", errors="replace").strip()
