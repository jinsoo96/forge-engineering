"""Runner — Inner Loop.

Wraps a baseline coding agent (e.g. Claude Code CLI) and produces a structured
run record. Runner holds NO write access to CLAUDE.md or any writable_surface
path declared in FORGE.md — that separation is the first Stochastic Inertia
defense tier.

For v0 this is a minimal shell-subprocess wrapper. A production runner would
stream tool calls, record state transitions as a graph, and enforce sandbox.
"""
from __future__ import annotations

import json
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

RUNS_DIR = Path.cwd() / "runs"


def execute_task(task_path: str) -> dict[str, Any]:
    """Run one task in the Inner Loop and return a run record.

    The returned dict conforms to schemas/run.v1.json.
    """
    run_id = str(uuid.uuid4())
    start = time.time()

    task_text = Path(task_path).read_text()

    # Baseline agent invocation — placeholder subprocess call. Replace with
    # actual Claude Code / Aider / custom agent driver in real deployment.
    proc = subprocess.run(
        ["claude", "-p", task_text],
        capture_output=True,
        text=True,
        timeout=600,
    )

    outcome = _classify_outcome(proc.returncode, proc.stdout, proc.stderr)

    record: dict[str, Any] = {
        "run_id": run_id,
        "task_path": task_path,
        "goal": task_text.splitlines()[0][:200] if task_text else "",
        "started_at": start,
        "duration_s": time.time() - start,
        "outcome": outcome,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
        "exit_code": proc.returncode,
        "harness_sha": _current_harness_sha(),
    }

    RUNS_DIR.mkdir(exist_ok=True)
    (RUNS_DIR / f"{run_id}.json").write_text(json.dumps(record, indent=2))
    return record


def _classify_outcome(code: int, stdout: str, stderr: str) -> str:
    if code == 0 and "FAIL" not in stdout.upper():
        return "success"
    if "PARTIAL" in stdout.upper():
        return "partial"
    return "failure"


def _current_harness_sha() -> str:
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    return out.stdout.strip() or "uncommitted"
