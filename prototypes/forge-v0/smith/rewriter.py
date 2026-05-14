"""Rewriter — converts a Reflection into a harness Rewrite Proposal.

Pipeline:
    Reflection → draft diff (LLM) → Cross-Check Validator → Ontology Gate →
    write file → git branch + commit (FORGE.md §3 trailer format).

Does NOT itself merge or run the benchmark — that is the Inertia Brake's job.
"""
from __future__ import annotations

import json
import subprocess
import textwrap
import uuid
from pathlib import Path
from typing import Any

from ._llm import call_json, DEFAULT_MODEL
from . import ontology_gate
from . import validator as _validator

PROPOSALS_DIR = Path.cwd() / "forge" / "proposals"

REWRITE_SYSTEM = """You are the Rewriter in a Forge Engineering runtime.

Given a structured reflection + the current contents of the target harness
file, produce one minimal append-only change.

Rules:
- No speculative edits. Every added line must trace to the lesson.
- Prefer additive changes (new bullet, new short section) over rewrites.
- If the target file is empty/new, propose a small initial scaffold (≤15 lines).
- Output strict JSON only, no fences, no prose:

{
  "new_content": "<full new file contents>",
  "expected_effect": "<≤200 chars>"
}
"""


def propose_rewrite(
    reflection: dict[str, Any],
    work_dir: str | Path | None = None,
    skip_validator: bool = False,
) -> dict[str, Any]:
    """Draft a rewrite, validate, gate, and commit on a forge/<id> branch."""
    PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)
    proposal_id = str(uuid.uuid4())
    branch = f"forge/{proposal_id[:8]}"

    candidates = reflection.get("rewrite_candidates") or []
    if not candidates:
        raise RuntimeError("reflection has no rewrite_candidates — nothing to propose")

    target_path = _resolve_target(candidates[0]["target"], work_dir)
    new_content, expected = _draft_rewrite(reflection, target_path)
    diff_text = _diff_text(target_path, new_content)

    proposal: dict[str, Any] = {
        "proposal_id": proposal_id,
        "derived_from_reflection": reflection["run_id"],
        "target_artifact_path": str(target_path),
        "branch": branch,
        "diff": diff_text,
        "expected_effect": expected,
        "status": "proposed",
    }

    # Cross-Check Validator
    verdict = (
        {"verdict": "skipped", "agreement": False, "reasons": ["validator skipped"], "minimality_score": 0.0}
        if skip_validator
        else _validator.validate_proposal(reflection, proposal)
    )
    proposal["validator_verdict"] = verdict

    # Ontology Gate
    gate_result = ontology_gate.check(reflection, proposal)
    proposal["ontology_check"] = gate_result

    if not skip_validator and verdict.get("verdict") == "reject":
        proposal["status"] = "rejected_by_validator"
        (PROPOSALS_DIR / f"{proposal_id}.json").write_text(json.dumps(proposal, indent=2))
        return proposal
    if not gate_result["pass"]:
        proposal["status"] = "rejected_by_ontology"
        (PROPOSALS_DIR / f"{proposal_id}.json").write_text(json.dumps(proposal, indent=2))
        return proposal

    _apply_change(branch, target_path, new_content, reflection, proposal_id, verdict, gate_result)
    (PROPOSALS_DIR / f"{proposal_id}.json").write_text(json.dumps(proposal, indent=2))
    return proposal


def _resolve_target(symbolic: str, work_dir: str | Path | None) -> Path:
    base = Path(work_dir).resolve() if work_dir else Path.cwd()
    mapping = {
        "system_prompt": base / "CLAUDE.md",
        "agents_md": base / "AGENTS.md",
        "workflow": base / "workflows.yaml",
        "skill_library": base / "skills" / "auto.md",
        "tool_spec": base / "tools" / "auto.md",
    }
    return mapping.get(symbolic, base / "CLAUDE.md")


def _draft_rewrite(reflection: dict[str, Any], target: Path) -> tuple[str, str]:
    current = target.read_text() if target.exists() else ""
    payload = {
        "reflection": reflection,
        "target_path": str(target),
        "current_content": current,
    }
    result = call_json(REWRITE_SYSTEM, json.dumps(payload, indent=2), model=DEFAULT_MODEL)
    new_content = result.get("new_content")
    expected = result.get("expected_effect", "")
    if not new_content:
        raise RuntimeError(f"rewriter returned no new_content: {result}")
    return new_content, expected


def _diff_text(target: Path, new_content: str) -> str:
    import difflib
    current = target.read_text().splitlines(keepends=True) if target.exists() else []
    new = new_content.splitlines(keepends=True)
    return "".join(difflib.unified_diff(current, new, fromfile=f"a/{target}", tofile=f"b/{target}"))


def _apply_change(
    branch: str,
    target: Path,
    new_content: str,
    reflection: dict[str, Any],
    proposal_id: str,
    verdict: dict[str, Any],
    gate: dict[str, Any],
) -> None:
    subprocess.run(["git", "checkout", "-B", branch], check=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(new_content)
    subprocess.run(["git", "add", str(target)], check=True)

    lesson_first = reflection["lesson"].splitlines()[0][:70]
    agreement = "yes" if verdict.get("agreement") else ("skipped" if verdict.get("verdict") == "skipped" else "no")
    ont = "pass" if gate.get("pass") else "fail"

    commit_message = textwrap.dedent(
        f"""
        forge(harness_rewrite): {lesson_first}

        Derived-From-Reflection: {reflection['run_id']}
        Proposal-Id: {proposal_id}
        Lesson: {reflection['lesson']}
        Validator-Agreement: {agreement}
        Validator-Minimality: {verdict.get('minimality_score', 'n/a')}
        Ontology-Check: {ont}
        Rollback-If: bench_delta < -0.05
        """
    ).strip()
    subprocess.run(["git", "commit", "-m", commit_message], check=True)
