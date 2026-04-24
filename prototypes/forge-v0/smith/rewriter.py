"""Rewriter — converts a Reflection into a harness Rewrite Proposal.

Writes a proposed diff on a dedicated `forge/<proposal_id>` git branch. Commit
message follows FORGE.md §3 format. The Inertia Brake decides whether to
merge or revert.
"""
from __future__ import annotations

import json
import subprocess
import textwrap
import uuid
from pathlib import Path
from typing import Any

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None  # type: ignore

PROPOSALS_DIR = Path.cwd() / "forge" / "proposals"

REWRITE_PROMPT = """You are the Rewriter in a Forge Engineering runtime.

Given a structured reflection, produce a minimal unified-diff-style patch to
the target harness file. Change only what the reflection justifies.

Rules:
- No speculative edits. Every line changed must be traceable to the lesson.
- Prefer additive changes (new bullet, new section) over in-place rewrites.
- Never modify files listed in locked_surface (check FORGE.md).
- Output JSON only: {"diff": "<unified diff>", "expected_effect": "..."}.
""".strip()


def propose_rewrite(reflection: dict[str, Any]) -> dict[str, Any]:
    PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)
    proposal_id = str(uuid.uuid4())
    branch = f"forge/{proposal_id[:8]}"

    candidate = reflection["rewrite_candidates"][0]
    target_path = _resolve_target(candidate["target"])

    diff_text, expected = _draft_diff(reflection, target_path)
    _apply_diff(branch, target_path, diff_text, reflection, proposal_id)

    proposal = {
        "proposal_id": proposal_id,
        "derived_from_reflection": reflection["run_id"],
        "target_artifact_path": str(target_path),
        "branch": branch,
        "diff": diff_text,
        "expected_effect": expected,
        "status": "proposed",
    }
    (PROPOSALS_DIR / f"{proposal_id}.json").write_text(json.dumps(proposal, indent=2))
    return proposal


def _resolve_target(symbolic: str) -> Path:
    mapping = {
        "system_prompt": Path("CLAUDE.md"),
        "agents_md": Path("AGENTS.md"),
        "workflow": Path("workflows.yaml"),
    }
    return mapping.get(symbolic, Path("CLAUDE.md"))


def _draft_diff(reflection: dict[str, Any], target: Path) -> tuple[str, str]:
    if Anthropic is None:
        raise RuntimeError("anthropic SDK not installed")
    client = Anthropic()

    current = target.read_text() if target.exists() else ""
    payload = {
        "reflection": reflection,
        "target_path": str(target),
        "current_content": current,
    }

    resp = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=2048,
        system=REWRITE_PROMPT,
        messages=[{"role": "user", "content": json.dumps(payload, indent=2)}],
    )
    parsed = json.loads(resp.content[0].text.strip())
    return parsed["diff"], parsed["expected_effect"]


def _apply_diff(
    branch: str, target: Path, diff_text: str, reflection: dict[str, Any], proposal_id: str
) -> None:
    subprocess.run(["git", "checkout", "-b", branch], check=True)
    subprocess.run(["git", "apply", "-"], input=diff_text, text=True, check=True)
    subprocess.run(["git", "add", str(target)], check=True)

    commit_message = textwrap.dedent(
        f"""
        forge(harness_rewrite): {reflection['lesson'].splitlines()[0][:70]}

        Derived-From-Reflection: {reflection['run_id']}
        Proposal-Id: {proposal_id}
        Lesson: {reflection['lesson']}
        Ontology-Check: pending
        Validator-Agreement: pending
        """
    ).strip()
    subprocess.run(["git", "commit", "-m", commit_message], check=True)
