"""Cross-Check Validator — independent second model reviews a proposal.

A core Forge safety mechanism: the Smith's reflection + rewrite is reviewed by
a *different* model family / size before the Inertia Brake even sees the diff.
This is FORGE.md §2 "Cross-check, must_differ_from_smith: true".

Output is a structured verdict: {approve, reject} + reasons. The Rewriter
embeds this into the commit trailer (`Validator-Agreement: yes|no`).
"""
from __future__ import annotations

import json
from typing import Any

from ._llm import call_json, DEFAULT_VALIDATOR_MODEL

SYSTEM_PROMPT = """You are the Cross-Check Validator in a Forge Engineering runtime.

You receive (a) a Reflection JSON and (b) a proposed diff to a harness file.
You must independently judge:
  - Is the root cause analysis grounded in the trace?
  - Does the diff address that root cause (and only that)?
  - Could this regress unrelated behavior?
  - Is the diff minimal (fewest lines that fix the lesson)?

You MUST output strict JSON with this exact shape — no prose, no fences:

{
  "verdict": "approve" | "reject",
  "agreement": true | false,
  "reasons": ["<≤120 chars>", ...],
  "regression_risks": ["<≤120 chars>", ...],
  "minimality_score": <float in [0,1]>
}

verdict=approve ⇒ agreement=true. verdict=reject ⇒ agreement=false. Be strict:
approve only if the diff cleanly addresses the lesson with no speculative edits.
"""


def validate_proposal(reflection: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
    """Return a validator verdict dict.

    Uses a model that MUST differ from the Smith's reflection model (see
    DEFAULT_VALIDATOR_MODEL).
    """
    payload = {
        "reflection": {
            "goal": reflection.get("goal"),
            "outcome": reflection.get("outcome"),
            "root_cause_analysis": reflection.get("root_cause_analysis"),
            "lesson": reflection.get("lesson"),
            "rewrite_candidates": reflection.get("rewrite_candidates", []),
        },
        "proposal": {
            "target_artifact_path": proposal.get("target_artifact_path"),
            "expected_effect": proposal.get("expected_effect"),
            "diff": proposal.get("diff"),
        },
    }
    user = json.dumps(payload, indent=2)
    verdict = call_json(SYSTEM_PROMPT, user, model=DEFAULT_VALIDATOR_MODEL)
    # Defensive sanitization
    if "verdict" not in verdict:
        verdict = {"verdict": "reject", "agreement": False, "reasons": ["malformed verdict"], "regression_risks": [], "minimality_score": 0.0}
    verdict.setdefault("agreement", verdict["verdict"] == "approve")
    verdict.setdefault("reasons", [])
    verdict.setdefault("regression_risks", [])
    verdict.setdefault("minimality_score", 0.0)
    return verdict
