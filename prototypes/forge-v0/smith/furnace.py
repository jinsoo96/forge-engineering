"""Failure Furnace — collects and classifies runs into the Forge Queue.

Non-goals in v0:
    - full state-transition graph extraction (listed as Phase 1.2 upgrade)
    - cross-run pattern induction (Phase 2 via Agent Workflow Memory)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

QUEUE_PATH = Path.cwd() / "forge" / "queue.jsonl"


def ingest_run(run_record: dict[str, Any]) -> None:
    """Append a classified run to the Forge Queue."""
    QUEUE_PATH.parent.mkdir(exist_ok=True)

    priority = _prioritize(run_record)
    entry = {
        "run_id": run_record["run_id"],
        "priority": priority,
        "outcome": run_record["outcome"],
        "harness_sha": run_record["harness_sha"],
    }
    with QUEUE_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def _prioritize(record: dict[str, Any]) -> str:
    if record["outcome"] == "failure":
        if _is_recurring(record):
            return "urgent"
        return "high"
    if record["outcome"] == "partial":
        return "medium"
    return "low"


def _is_recurring(record: dict[str, Any]) -> bool:
    """Check whether a similar failure appeared in the last 20 runs.

    Simple v0 heuristic: same stderr tail signature.
    Phase 2 upgrade: embedding similarity on state-transition graphs.
    """
    runs_dir = Path.cwd() / "runs"
    if not runs_dir.exists():
        return False
    signature = (record.get("stderr_tail") or "")[:200]
    if not signature:
        return False

    recent = sorted(runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]
    count = 0
    for path in recent:
        if path.stem == record["run_id"]:
            continue
        try:
            other = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        if (other.get("stderr_tail") or "")[:200] == signature:
            count += 1
    return count >= 1
