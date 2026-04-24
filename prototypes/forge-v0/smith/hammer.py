"""Reflection Hammer — generates structured Reflection JSON.

Calls Claude API via the anthropic SDK. Enforces Reflection Schema. Retries
up to 3 times on schema violation.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from anthropic import Anthropic
    import jsonschema
except ImportError:
    Anthropic = None  # type: ignore
    jsonschema = None  # type: ignore

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "reflection.v1.json"

SYSTEM_PROMPT = """You are the Reflection Hammer in a Forge Engineering runtime.

You read an agent run record and output a single JSON object conforming to the
Reflection Schema. No prose. No backticks. Valid JSON only.

Goals:
1. Identify WHERE the run failed (or underperformed) with specificity.
2. Identify WHY — root cause, not symptom.
3. State a LESSON in at most 3 lines.
4. Propose concrete rewrite_candidates pointing at harness artifacts that, if
   edited, would prevent recurrence.
5. Assign a confidence in [0, 1].

Never invent facts not present in the trace. If unsure, lower confidence.
""".strip()


def reflect(run_record: dict[str, Any]) -> dict[str, Any]:
    if Anthropic is None:
        raise RuntimeError("anthropic SDK not installed; pip install anthropic")

    schema = json.loads(SCHEMA_PATH.read_text())
    client = Anthropic()

    user_payload = json.dumps(
        {
            "run_id": run_record["run_id"],
            "goal": run_record["goal"],
            "outcome": run_record["outcome"],
            "stdout_tail": run_record.get("stdout_tail", ""),
            "stderr_tail": run_record.get("stderr_tail", ""),
            "exit_code": run_record.get("exit_code"),
        },
        indent=2,
    )

    for attempt in range(3):
        resp = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_payload}],
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
        )
        text = resp.content[0].text.strip()
        try:
            candidate = json.loads(text)
        except json.JSONDecodeError:
            continue

        if jsonschema is None:
            return candidate  # trust fallback
        try:
            jsonschema.validate(candidate, schema)
            return candidate
        except jsonschema.ValidationError as exc:
            user_payload = (
                f"Previous output did not validate: {exc.message}\n\n"
                f"Try again. Output JSON only.\n\nRun:\n{user_payload}"
            )
            continue

    raise RuntimeError("reflection did not validate after 3 attempts")
