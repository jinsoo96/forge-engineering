"""Ontology Gate — symbolic invariants over reflections/proposals.

Reads ontology/invariants.json and enforces each invariant against the live
reflection + proposal pair. A failure aborts the rewrite before it touches the
git tree.

FORGE.md §2.6: the ontology gate is required when ontology/core.ttl is present.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

INVARIANTS_PATH = Path(__file__).resolve().parent.parent / "ontology" / "invariants.json"


def check(reflection: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
    """Return {pass: bool, violations: [...]} after running all invariants."""
    if not INVARIANTS_PATH.exists():
        return {"pass": True, "violations": [], "note": "ontology absent — gate skipped"}

    spec = json.loads(INVARIANTS_PATH.read_text())
    violations: list[dict[str, str]] = []

    for inv in spec["invariants"]:
        applies = inv["applies_to"]
        if applies == "proposal":
            ok, why = _check_proposal_invariant(inv, proposal)
        elif applies == "reflection":
            ok, why = _check_reflection_invariant(inv, reflection)
        else:
            # commit / benchmark_delta invariants are checked elsewhere
            continue
        if not ok:
            violations.append({"id": inv["id"], "name": inv["name"], "reason": why})

    return {"pass": not violations, "violations": violations}


def _check_proposal_invariant(inv: dict, proposal: dict[str, Any]) -> tuple[bool, str]:
    if inv["check"] == "required_field":
        present = bool(proposal.get(inv["field"]))
        return present, ("" if present else inv["violation_message"])
    if inv["check"] == "path_not_in_locked":
        path = proposal.get("target_artifact_path", "")
        for locked in inv["locked_paths"]:
            if locked.endswith("/") and path.startswith(locked):
                return False, inv["violation_message"]
            if path == locked or path.endswith("/" + locked):
                return False, inv["violation_message"]
        return True, ""
    return True, ""


def _check_reflection_invariant(inv: dict, reflection: dict[str, Any]) -> tuple[bool, str]:
    if inv["check"] == "min_numeric":
        val = reflection.get(inv["field"])
        if val is None:
            return False, f"missing {inv['field']}"
        return (val >= inv["min"]), ("" if val >= inv["min"] else inv["violation_message"])
    return True, ""
