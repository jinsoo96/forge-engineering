"""forge — command-line interface for the Forge runtime.

Commands:
    forge init                Initialize a Forge-compliant repo.
    forge watch <task>        Run Runner + Smith loop (full pipeline) on a task.
    forge log                 Show the harness-commit timeline.
    forge rollback <sha>      Manually revert a harness commit.
    forge bench               Evaluate current harness against bench/fixed/*.
    forge temper <component>  Generate prompt-tempering candidates.
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


def cmd_init(_args):
    RUNS_DIR.mkdir(exist_ok=True)
    (FORGE_ROOT / "forge").mkdir(exist_ok=True)
    COMMITS_LOG.touch(exist_ok=True)
    if not FORGE_CONFIG.exists():
        print(f"warning: {FORGE_CONFIG} missing — copy from spec/FORGE.md template", file=sys.stderr)
        return 1
    print("forge: initialized.")
    return 0


def cmd_watch(args):
    from runner.runner import execute_task
    from smith.furnace import ingest_run
    from smith.hammer import reflect
    from smith.rewriter import propose_rewrite
    from safety.inertia_brake import check_or_rollback

    run_record = execute_task(args.task, work_dir=args.work_dir)
    ingest_run(run_record)

    if run_record["outcome"] == "success":
        print(json.dumps({"outcome": "success", "note": "no rewrite triggered"}, indent=2))
        return 0

    reflection = reflect(run_record)
    if not reflection.get("rewrite_candidates"):
        print(json.dumps({"outcome": run_record["outcome"], "note": "lesson-only reflection"}, indent=2))
        return 0

    proposal = propose_rewrite(reflection, work_dir=args.work_dir)
    if proposal["status"].startswith("rejected_"):
        print(json.dumps({"proposal_id": proposal["proposal_id"], "status": proposal["status"]}, indent=2))
        return 0

    verdict = check_or_rollback(proposal)
    print(json.dumps({"proposal_id": proposal["proposal_id"], "verdict": verdict}, indent=2))
    return 0


def cmd_log(_args):
    if not COMMITS_LOG.exists() or COMMITS_LOG.stat().st_size == 0:
        print("forge: no commits yet.")
        return 0
    for line in COMMITS_LOG.read_text().splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        print(f"{e['timestamp']}  {e['proposal_id'][:8]}  {e['mechanism']}  "
              f"J: {e['bench_before']:.3f} → {e['bench_after']:.3f}  ({e['verdict']})")
    return 0


def cmd_rollback(args):
    subprocess.run(["git", "revert", "--no-edit", args.commit_sha], check=True)
    return 0


def cmd_bench(_args):
    from safety.inertia_brake import measure_benchmark
    score = measure_benchmark()
    print(f"forge: J(H) = {score:.4f}")
    return 0


def cmd_temper(args):
    from smith.tempering import propose_addenda, collect_reflections
    target = Path(args.target_prompt_file).read_text() if args.target_prompt_file else ""
    reflections = collect_reflections(limit=args.limit)
    result = propose_addenda(target, reflections)
    print(json.dumps(result, indent=2))
    return 0


def main():
    p = argparse.ArgumentParser(prog="forge")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("init").set_defaults(func=cmd_init)

    watch = sub.add_parser("watch")
    watch.add_argument("task", help="path to task description (markdown)")
    watch.add_argument("--work-dir", help="working directory the runner operates in", default=None)
    watch.set_defaults(func=cmd_watch)

    sub.add_parser("log").set_defaults(func=cmd_log)

    rb = sub.add_parser("rollback")
    rb.add_argument("commit_sha")
    rb.set_defaults(func=cmd_rollback)

    sub.add_parser("bench").set_defaults(func=cmd_bench)

    tmp = sub.add_parser("temper")
    tmp.add_argument("--target-prompt-file", help="file containing the target prompt", default=None)
    tmp.add_argument("--limit", type=int, default=10)
    tmp.set_defaults(func=cmd_temper)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
