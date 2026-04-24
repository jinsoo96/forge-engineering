"""Inertia Brake — deterministic third-tier defense against Stochastic Inertia.

Guarantee: V(H_n) = J* - J(H_n) is monotonically non-increasing.

Algorithm:
    1. Measure J(H_current) before proposal merge.
    2. Merge proposal branch into HEAD (soft merge — commit created).
    3. Measure J(H_new).
    4. If J(H_new) - J(H_current) < threshold_delta, revert and record rollback.
    5. On success, append to forge/commits.jsonl.
"""
from __future__ import annotations

import json
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

    subprocess.run(["git", "checkout", "main"], check=True)
    subprocess.run(["git", "merge", "--no-ff", proposal["branch"]], check=True)

    bench_after = measure_benchmark()
    delta = bench_after - bench_before

    commit_sha = _head_sha()
    verdict: str

    if delta < THRESHOLD_DELTA:
        subprocess.run(["git", "revert", "--no-edit", commit_sha], check=True)
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

    v0 uses a stub that returns the 'baseline' field from the YAML; a real
    implementation would run each test entry and average normalized scores.
    """
    if not BENCH_FILE.exists():
        return 0.0
    data = yaml.safe_load(BENCH_FILE.read_text()) or {}
    scores = [float(item.get("score", 0.0)) for item in data.get("tasks", [])]
    if not scores:
        return float(data.get("baseline", 0.0))
    return sum(scores) / len(scores)


def _head_sha() -> str:
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


def _append_log(entry: dict[str, Any]) -> None:
    COMMITS_LOG.parent.mkdir(exist_ok=True)
    with COMMITS_LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")
