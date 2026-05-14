"""Runner — Inner Loop.

Wraps a baseline coding agent (Claude Code CLI) executing in a target work
directory. Runner holds NO write access to the meta-harness (FORGE.md, smith/,
schemas/, bench/) — only to the work_dir. That separation is the first
Stochastic Inertia defense tier.

The outcome is determined empirically: how many pytest tests pass *after* the
agent runs vs. before. This makes the run record falsifiable.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

RUNS_DIR = Path.cwd() / "runs"
DEFAULT_TIMEOUT = 600


def execute_task(task_path: str, work_dir: str | None = None, model: str = "claude-opus-4-7") -> dict[str, Any]:
    """Run one task in the Inner Loop and return a run record (schemas/run.v1.json)."""
    run_id = str(uuid.uuid4())
    start = time.time()

    task_text = Path(task_path).read_text()
    wd = Path(work_dir).resolve() if work_dir else Path.cwd()

    before_passed, before_total = _pytest_score(wd)

    cmd = [
        "claude",
        "-p",
        "--model", model,
        "--output-format", "json",
        "--no-session-persistence",
        "--add-dir", str(wd),
        "--permission-mode", "bypassPermissions",
        task_text,
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=DEFAULT_TIMEOUT,
            cwd=str(wd),
        )
        agent_stdout = proc.stdout
        agent_stderr = proc.stderr
        exit_code = proc.returncode
    except subprocess.TimeoutExpired as exc:
        agent_stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        agent_stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        exit_code = 124

    # Surface the agent's `result` text if the envelope is JSON.
    agent_result_text = agent_stdout
    try:
        envelope = json.loads(agent_stdout)
        if isinstance(envelope, dict) and "result" in envelope:
            agent_result_text = envelope["result"] or ""
    except json.JSONDecodeError:
        pass

    after_passed, after_total = _pytest_score(wd)
    outcome = _classify_by_delta(before_passed, after_passed, after_total)

    record: dict[str, Any] = {
        "run_id": run_id,
        "task_path": task_path,
        "goal": task_text.splitlines()[0][:200] if task_text else "",
        "started_at": start,
        "duration_s": time.time() - start,
        "outcome": outcome,
        "stdout_tail": agent_result_text[-4000:],
        "stderr_tail": agent_stderr[-4000:],
        "exit_code": exit_code,
        "harness_sha": _current_harness_sha(),
        "work_dir": str(wd),
        "pytest_before": {"passed": before_passed, "total": before_total},
        "pytest_after": {"passed": after_passed, "total": after_total},
    }

    RUNS_DIR.mkdir(exist_ok=True)
    (RUNS_DIR / f"{run_id}.json").write_text(json.dumps(record, indent=2))
    return record


_PYTEST_TAIL_RE = re.compile(r"(\d+) failed.*?(\d+) passed|(\d+) passed", re.S)


def _pytest_score(wd: Path) -> tuple[int, int]:
    """Return (passed, total) for the given work dir. (0, 0) if pytest absent."""
    pytest_bin = _find_pytest()
    if not pytest_bin or not (wd / "tests").exists():
        return (0, 0)
    try:
        proc = subprocess.run(
            [pytest_bin, "--tb=no", "-rN", "-o", "addopts="],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(wd),
        )
    except subprocess.TimeoutExpired:
        return (0, 0)
    return _parse_pytest_summary(proc.stdout + proc.stderr)


def _parse_pytest_summary(text: str) -> tuple[int, int]:
    passed = failed = errors = 0
    for tok, kind in re.findall(r"(\d+)\s+(passed|failed|errors?)", text):
        n = int(tok)
        if kind == "passed":
            passed = n
        elif kind == "failed":
            failed = n
        elif kind.startswith("error"):
            errors = n
    total = passed + failed + errors
    return (passed, total)


def _find_pytest() -> str | None:
    """Prefer the project venv, then PATH."""
    candidates = [
        Path.cwd() / ".venv" / "bin" / "pytest",
        Path.home() / ".local" / "bin" / "pytest",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    from shutil import which
    return which("pytest")


def _classify_by_delta(before: int, after: int, total: int) -> str:
    if total == 0:
        return "failure"
    if after == total:
        return "success"
    if after > before:
        return "partial"
    return "failure"


def _current_harness_sha() -> str:
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    return out.stdout.strip() or "uncommitted"
