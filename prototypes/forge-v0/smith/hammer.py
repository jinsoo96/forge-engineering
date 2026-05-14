"""Reflection Hammer — generates structured Reflection JSON.

Calls the shared LLM wrapper (smith/_llm.py). Enforces Reflection Schema via
the CLI's --json-schema and retries up to 3 times on validation failure.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import jsonschema
except ImportError:
    jsonschema = None  # type: ignore

from ._llm import call_json, DEFAULT_MODEL

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "reflection.v1.json"

_SCHEMA_SNIPPET = json.dumps(
    json.loads(SCHEMA_PATH.read_text()), indent=2, ensure_ascii=False
)

SYSTEM_PROMPT = f"""You are the Reflection Hammer in a Forge Engineering runtime.

Read an agent run record and output a single JSON object that MUST validate
against the JSON Schema below. Output JSON only — no prose, no code fences, no
markdown. Field names and enums are literal.

=== REFLECTION SCHEMA v1 ===
{_SCHEMA_SNIPPET}
=== END SCHEMA ===

Rules:
1. Top-level keys: run_id, goal, outcome, root_cause_analysis, lesson,
   confidence (rewrite_candidates optional). Copy run_id, goal, outcome from
   the input verbatim.
2. root_cause_analysis MUST have where_failed, why_failed, evidence (array, ≥1).
3. rewrite_candidates items use EXACT keys: target, change_type, rationale.
   target ∈ {{system_prompt, tool_spec, workflow, agents_md, skill_library}}.
   change_type ∈ {{add, modify, remove}}.
4. lesson: ≤ 3 lines, actionable, what to do differently next time.
5. confidence: float in [0, 1]. Lower when trace is ambiguous.
6. Never invent facts absent from the trace.
""".strip()


def reflect(run_record: dict[str, Any]) -> dict[str, Any]:
    schema = json.loads(SCHEMA_PATH.read_text())

    payload = {
        "run_id": run_record["run_id"],
        "goal": run_record["goal"],
        "outcome": run_record["outcome"],
        "stdout_tail": run_record.get("stdout_tail", ""),
        "stderr_tail": run_record.get("stderr_tail", ""),
        "exit_code": run_record.get("exit_code"),
        "pytest_before": run_record.get("pytest_before"),
        "pytest_after": run_record.get("pytest_after"),
    }
    user = json.dumps(payload, indent=2)

    last_err = ""
    last_text = ""
    for _attempt in range(3):
        try:
            candidate = call_json(SYSTEM_PROMPT, user, model=DEFAULT_MODEL)
        except Exception as exc:
            last_err = f"transport error: {exc}"
            user = (
                f"Previous call failed: {exc}.\nOutput JSON ONLY per schema.\n\nRun:\n{user}"
            )
            continue
        last_text = json.dumps(candidate)

        # Defensive: model might wrap result; unwrap if there's exactly one matching field.
        if not all(k in candidate for k in ("run_id", "goal", "outcome", "root_cause_analysis")):
            for v in candidate.values():
                if isinstance(v, dict) and all(k in v for k in ("run_id", "goal", "outcome")):
                    candidate = v
                    break

        if jsonschema is None:
            return candidate
        try:
            jsonschema.validate(candidate, schema)
            return candidate
        except jsonschema.ValidationError as exc:
            last_err = f"schema violation: {exc.message}"
            user = (
                f"Previous output did not validate: {exc.message}\n\n"
                f"Try again. Output JSON ONLY per schema.\n\nRun:\n{user}"
            )
            continue

    raise RuntimeError(
        f"reflection did not validate after 3 attempts. Last error: {last_err}\n"
        f"--- last raw output (tail) ---\n{last_text[-800:]}"
    )
