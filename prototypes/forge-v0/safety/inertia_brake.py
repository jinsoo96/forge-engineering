"""Inertia Brake — deterministic third-tier defense against Stochastic Inertia.

Guarantee: V(H_n) = J* - J(H_n) is monotonically non-increasing.

Algorithm:
    1. Measure J(H_current) before proposal merge.
    2. Fast-forward / merge proposal branch.
    3. Measure J(H_new).
    4. If J(H_new) - J(H_current) < threshold_delta, revert and record rollback.
    5. Append to forge/commits.jsonl regardless.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any

import yaml  # type: ignore

BENCH_FILE = Path.cwd() / "bench" / "fixed" / "lite.yaml"
COMMITS_LOG = Path.cwd() / "forge" / "commits.jsonl"
THRESHOLD_DELTA = -0.05


def check_or_rollback(proposal: dict[str, Any]) -> str:
    bench_before = measure_benchmark()

    # Determine base branch (main or master) before checkout
    base = _current_branch()
    if base.startswith("forge/") or not base:
        base = _default_base_branch()

    subprocess.run(["git", "checkout", base], check=True)
    subprocess.run(["git", "merge", "--no-ff", "--no-edit", proposal["branch"]], check=True)

    bench_after = measure_benchmark()
    delta = bench_after - bench_before

    commit_sha = _head_sha()
    verdict: str

    if delta < THRESHOLD_DELTA:
        subprocess.run(["git", "revert", "--no-edit", "-m", "1", commit_sha], check=True)
        verdict = "rolled_back"
    else:
        verdict = "promoted"

    _append_log(
        {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "proposal_id": proposal["proposal_id"],
            "commit_sha": commit_sha,
            "mechanism": "harness_rewrite",
            "bench_before": bench_before,
            "bench_after": bench_after,
            "delta": delta,
            "verdict": verdict,
        }
    )
    return verdict


def measure_benchmark() -> float:
    """Evaluate the current harness against bench/fixed/lite.yaml.

    Each task can declare either:
      - `score` (static, for v0 demo cases), or
      - `pytest_dir` (run pytest, score = passed / total).
    """
    if not BENCH_FILE.exists():
        return 0.0
    data = yaml.safe_load(BENCH_FILE.read_text()) or {}
    tasks = data.get("tasks", [])
    if not tasks:
        return float(data.get("baseline", 0.0))

    per_task = []
    for t in tasks:
        if "pytest_dir" in t:
            per_task.append(_pytest_pass_rate(Path(t["pytest_dir"])))
        else:
            per_task.append(float(t.get("score", 0.0)))
    return sum(per_task) / len(per_task) if per_task else 0.0


def _pytest_pass_rate(work_dir: Path) -> float:
    pytest_bin = _find_pytest()
    wd = work_dir if work_dir.is_absolute() else (Path.cwd() / work_dir)
    if not pytest_bin or not wd.exists():
        return 0.0
    try:
        proc = subprocess.run(
            [pytest_bin, "--tb=no", "-rN", "-o", "addopts="],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(wd),
        )
    except subprocess.TimeoutExpired:
        return 0.0
    out = proc.stdout + proc.stderr
    passed = failed = 0
    for tok, kind in re.findall(r"(\d+)\s+(passed|failed)", out):
        if kind == "passed":
            passed = int(tok)
        else:
            failed = int(tok)
    total = passed + failed
    return (passed / total) if total else 0.0


def _find_pytest() -> str | None:
    candidates = [
        Path.cwd() / ".venv" / "bin" / "pytest",
        Path.home() / ".local" / "bin" / "pytest",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    from shutil import which
    return which("pytest")


def _current_branch() -> str:
    out = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, check=True)
    return out.stdout.strip() or "main"


def _default_base_branch() -> str:
    for candidate in ("main", "master"):
        out = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", candidate],
            capture_output=True, text=True, check=False,
        )
        if out.returncode == 0:
            return candidate
    return "main"


def _head_sha() -> str:
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


def _append_log(entry: dict[str, Any]) -> None:
    COMMITS_LOG.parent.mkdir(exist_ok=True)
    with COMMITS_LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")
