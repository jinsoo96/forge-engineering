"""forge — command-line interface for the Forge runtime.

Commands:
    forge init            Initialize a Forge-compliant repo (creates FORGE.md, runs/, forge/).
    forge watch <task>    Run Runner + Smith loop on a task.
    forge log             Show the harness-commit timeline.
    forge rollback <id>   Manually revert a specific harness commit.
    forge bench           Evaluate current harness against bench/fixed/*.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

FORGE_ROOT = Path.cwd()
FORGE_CONFIG = FORGE_ROOT / "FORGE.md"
RUNS_DIR = FORGE_ROOT / "runs"
COMMITS_LOG = FORGE_ROOT / "forge" / "commits.jsonl"


def cmd_init(_args: argparse.Namespace) -> int:
    RUNS_DIR.mkdir(exist_ok=True)
    (FORGE_ROOT / "forge").mkdir(exist_ok=True)
    COMMITS_LOG.touch(exist_ok=True)
    if not FORGE_CONFIG.exists():
        print(f"warning: {FORGE_CONFIG} missing — copy from spec/FORGE.md template", file=sys.stderr)
        return 1
    print("forge: initialized.")
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    from runner.runner import execute_task
    from smith.furnace import ingest_run
    from smith.hammer import reflect
    from smith.rewriter import propose_rewrite
    from safety.inertia_brake import check_or_rollback

    run_record = execute_task(args.task)
    ingest_run(run_record)

    if run_record["outcome"] == "success":
        print("forge: task succeeded; no rewrite triggered.")
        return 0

    reflection = reflect(run_record)
    if not reflection.get("rewrite_candidates"):
        print("forge: reflection produced lesson-only; no rewrite proposed.")
        return 0

    proposal = propose_rewrite(reflection)
    verdict = check_or_rollback(proposal)
    print(json.dumps({"proposal_id": proposal["proposal_id"], "verdict": verdict}, indent=2))
    return 0


def cmd_log(_args: argparse.Namespace) -> int:
    if not COMMITS_LOG.exists():
        print("forge: no commits yet.")
        return 0
    for line in COMMITS_LOG.read_text().splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        print(f"{entry['timestamp']}  {entry['proposal_id'][:8]}  {entry['mechanism']}  J={entry['bench_after']:.3f}")
    return 0


def cmd_rollback(args: argparse.Namespace) -> int:
    subprocess.run(["git", "revert", "--no-edit", args.commit_sha], check=True)
    return 0


def cmd_bench(_args: argparse.Namespace) -> int:
    from safety.inertia_brake import measure_benchmark
    score = measure_benchmark()
    print(f"forge: J(H) = {score:.4f}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="forge")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("init").set_defaults(func=cmd_init)

    watch = sub.add_parser("watch")
    watch.add_argument("task", help="path to task description (markdown)")
    watch.set_defaults(func=cmd_watch)

    sub.add_parser("log").set_defaults(func=cmd_log)

    rb = sub.add_parser("rollback")
    rb.add_argument("commit_sha")
    rb.set_defaults(func=cmd_rollback)

    sub.add_parser("bench").set_defaults(func=cmd_bench)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
