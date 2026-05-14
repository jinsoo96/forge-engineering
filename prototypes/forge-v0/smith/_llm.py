"""Unified LLM wrapper.

Routes every Smith-side LLM call through `claude -p --output-format json`. This
removes ANTHROPIC_API_KEY as a hard requirement (the CLI uses the user's OAuth
session) and gives every component a single debug surface.

Fallback chain:
    1. `claude -p` subprocess  (default — uses CLI credentials)
    2. `anthropic.Anthropic()` SDK if ANTHROPIC_API_KEY is set (explicit opt-in)
    3. RuntimeError with actionable message
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any

DEFAULT_MODEL = "claude-opus-4-7"
DEFAULT_VALIDATOR_MODEL = "claude-sonnet-4-6"


def call_json(
    system_prompt: str,
    user_message: str,
    model: str = DEFAULT_MODEL,
    json_schema: dict[str, Any] | None = None,
    timeout: int = 180,
) -> dict[str, Any]:
    """Call a model and return a parsed JSON dict.

    If `json_schema` is provided, the CLI enforces structured output.
    Raises RuntimeError if no transport succeeds or the result is not JSON.
    """
    if os.environ.get("FORGE_LLM_FORCE_SDK") == "1" and os.environ.get("ANTHROPIC_API_KEY"):
        return _call_via_sdk(system_prompt, user_message, model, json_schema)

    if shutil.which("claude"):
        try:
            return _call_via_cli(system_prompt, user_message, model, json_schema, timeout)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            last = exc
            if os.environ.get("ANTHROPIC_API_KEY"):
                return _call_via_sdk(system_prompt, user_message, model, json_schema)
            raise RuntimeError(f"claude CLI failed and no ANTHROPIC_API_KEY: {last}") from last

    if os.environ.get("ANTHROPIC_API_KEY"):
        return _call_via_sdk(system_prompt, user_message, model, json_schema)

    raise RuntimeError(
        "No LLM transport available. Install Claude CLI or set ANTHROPIC_API_KEY."
    )


def _call_via_cli(
    system_prompt: str,
    user_message: str,
    model: str,
    json_schema: dict[str, Any] | None,
    timeout: int,
) -> dict[str, Any]:
    cmd = [
        "claude",
        "-p",
        "--model", model,
        "--output-format", "json",
        "--no-session-persistence",
        "--disallowedTools=Bash,Edit,Write,NotebookEdit,Read,Glob,Grep,WebFetch,WebSearch,TodoWrite,Task",
        "--system-prompt", system_prompt,
    ]
    if json_schema is not None:
        cmd += ["--json-schema", json.dumps(json_schema)]
    cmd.append(user_message)

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    )
    envelope = json.loads(proc.stdout)
    # claude -p --output-format json returns an envelope; the assistant text is
    # in `result`.
    text = envelope.get("result") if isinstance(envelope, dict) else None
    if text is None:
        # newer CLIs may inline; try direct parse
        return envelope if isinstance(envelope, dict) else {"_raw": str(envelope)}
    return _parse_json_text(text)


def _call_via_sdk(
    system_prompt: str,
    user_message: str,
    model: str,
    json_schema: dict[str, Any] | None,
) -> dict[str, Any]:
    from anthropic import Anthropic  # type: ignore

    client = Anthropic()
    resp = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    text = resp.content[0].text
    return _parse_json_text(text)


def _parse_json_text(text: str) -> dict[str, Any]:
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return json.loads(t)
