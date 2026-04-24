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

_SCHEMA_SNIPPET = json.dumps(
    json.loads(SCHEMA_PATH.read_text()), indent=2, ensure_ascii=False
)

SYSTEM_PROMPT = f"""You are the Reflection Hammer in a Forge Engineering runtime.

You read an agent run record and output a single JSON object that MUST validate
against the following JSON Schema. Output JSON only — no prose, no code fences,
no markdown. Field names and enums are literal.

=== REFLECTION SCHEMA v1 ===
{_SCHEMA_SNIPPET}
=== END SCHEMA ===

Rules:
1. Top-level MUST include: run_id, goal, outcome, root_cause_analysis, lesson,
   confidence. Copy run_id, goal, outcome from the input verbatim.
2. root_cause_analysis MUST have where_failed, why_failed, evidence (array).
3. rewrite_candidates items MUST use EXACT keys: target, change_type, rationale.
   target MUST be one of: system_prompt, tool_spec, workflow, agents_md,
   skill_library. change_type MUST be one of: add, modify, remove.
4. lesson: ≤ 3 lines, actionable, what to do differently next time.
5. confidence: float in [0, 1]. Lower when trace is ambiguous.
6. Never invent facts not present in the trace.
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

    last_text = ""
    last_err = ""
    for _attempt in range(3):
        resp = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_payload}],
        )
        last_text = resp.content[0].text.strip()
        candidate_text = _strip_code_fence(last_text)

        try:
            candidate = json.loads(candidate_text)
        except json.JSONDecodeError as exc:
            last_err = f"JSON parse error: {exc}"
            user_payload = (
                f"Your previous output was not valid JSON ({exc}).\n"
                f"Output JSON ONLY, no markdown, no code fences.\n\nRun:\n{user_payload}"
            )
            continue

        if jsonschema is None:
            return candidate
        try:
            jsonschema.validate(candidate, schema)
            return candidate
        except jsonschema.ValidationError as exc:
            last_err = f"schema violation: {exc.message}"
            user_payload = (
                f"Previous output did not validate: {exc.message}\n\n"
                f"Try again. Output JSON ONLY per schema.\n\nRun:\n{user_payload}"
            )
            continue

    raise RuntimeError(
        f"reflection did not validate after 3 attempts. "
        f"Last error: {last_err}\n--- raw output (tail) ---\n{last_text[-800:]}"
    )


def _strip_code_fence(text: str) -> str:
    """Strip ```json ... ``` or ``` ... ``` wrappers if the model added them."""
    t = text.strip()
    if t.startswith("```"):
        # drop first line (``` or ```json) and trailing ```
        lines = t.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t
