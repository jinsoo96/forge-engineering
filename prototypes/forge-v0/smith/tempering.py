"""Prompt Tempering — TextGrad × Promptbreeder hybrid (Phase 2).

Reads recent reflections and synthesizes a 'textual gradient': a small natural-
language patch to the *prompts* the Smith itself runs on (Hammer system
prompt, Rewriter system prompt, etc).

This is Forge updating Forge. The proposed patch is still subject to:
    - Cross-Check Validator
    - Ontology Gate
    - Inertia Brake (does it improve J(H) on the fixed benchmark?)

Promptbreeder = mutation. TextGrad = gradient. Our hybrid: each iteration
generates K mutants via LLM-as-mutator using the reflections as "loss",
then picks the survivor by benchmark.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ._llm import call_json, DEFAULT_MODEL

RUNS_DIR = Path.cwd() / "runs"

SYSTEM_PROMPT = """You are the Prompt Tempering anvil.

Inputs: a target prompt (the current system prompt of a Smith component) and N
recent Reflection JSONs. Each reflection describes a failure or partial
success. Treat the union of root_cause_analysis fields as the gradient signal.

Output strict JSON only — no prose, no fences:

{
  "candidates": [
    {
      "id": "v1",
      "addendum": "<≤6 lines, appendable to the target prompt>",
      "rationale": "<≤200 chars: which reflection failure this addresses>"
    },
    ...
  ]
}

Generate exactly 3 candidates. Each addendum must be additive (append-only) and
self-contained — assume it will be concatenated to the existing prompt.
"""


def collect_reflections(limit: int = 10) -> list[dict[str, Any]]:
    if not RUNS_DIR.exists():
        return []
    files = sorted(RUNS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    out: list[dict[str, Any]] = []
    for p in files[: limit * 2]:
        try:
            data = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        if "root_cause_analysis" in data:
            out.append(data)
        if len(out) >= limit:
            break
    return out


def propose_addenda(target_prompt: str, reflections: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Generate 3 candidate addenda for the target prompt.

    Returns the LLM response dict; the caller decides which to keep.
    """
    reflections = reflections or collect_reflections()
    if not reflections:
        return {"candidates": [], "note": "no reflections available"}

    payload = {
        "target_prompt": target_prompt,
        "reflections": [
            {
                "lesson": r.get("lesson"),
                "root_cause_analysis": r.get("root_cause_analysis"),
                "outcome": r.get("outcome"),
                "confidence": r.get("confidence"),
            }
            for r in reflections
        ],
    }
    return call_json(SYSTEM_PROMPT, json.dumps(payload, indent=2), model=DEFAULT_MODEL)


def pick_survivor(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Tournament selector (v0 stub).

    For a real implementation, each candidate would be benchmark-evaluated and
    the winner returned. v0 returns the first candidate.
    """
    return candidates[0] if candidates else None
