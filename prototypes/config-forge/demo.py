"""10-step walkthrough — start from a deliberately weak config and watch the
self-forging loop raise the benchmark by evolving TYPED config knobs.

Run:  python demo.py
Offline, no API, deterministic. Asserts the FORGE success criteria.
"""
from __future__ import annotations

from algebra import Algebra
from bench import BENCH
from forge import forge_loop, measure
from runner import MockRunner

# Deliberately weak starting harness: judge off, threshold too low, no guards,
# shallow judge effort, single retry. The loop must discover the healthy profile.
INITIAL_CONFIG: dict = {
    "active_strategies": {"s08_decide:evaluation": "none", "s08_decide:decide": "threshold"},
    "validation_threshold": 0.5,
    "max_retries": 1,
    "guards": [],
    "criteria": [{"name": "relevance", "weight": 1.0, "hard": False}],
    "effort": {"s08_decide": "medium"},
}


def main() -> None:
    runner = MockRunner()
    algebra = Algebra()

    j0 = measure(runner, INITIAL_CONFIG, BENCH)
    final_config, history, commits = forge_loop(runner, algebra, BENCH, INITIAL_CONFIG, max_steps=12)
    jf = history[-1]

    print("=" * 72)
    print("CONFIG-FORGE — self-forging loop over a typed HarnessConfig")
    print("=" * 72)
    print(f"initial J = {j0:.4f}    final J = {jf:.4f}    gain = +{jf - j0:.4f}")
    print(f"J curve: {' -> '.join(f'{j:.3f}' for j in history)}")
    print("-" * 72)
    print(f"{'step':>4} {'verdict':>11} {'delta':>7}  move (lesson)")
    for c in commits:
        print(f"{c.step:>4} {c.verdict:>11} {c.delta:>+7.4f}  {c.move}")
        print(f"{'':>25}  └ {c.lesson}")
    print("-" * 72)

    promotes = [c for c in commits if c.verdict == "promoted"]
    rollbacks = [c for c in commits if c.verdict == "rolled_back"]
    print(f"promoted: {len(promotes)}   rolled_back: {len(rollbacks)}   log: forge/commits.jsonl")
    print("final config knobs:")
    print(f"  evaluation strategy = {final_config['active_strategies'].get('s08_decide:evaluation')}")
    print(f"  validation_threshold = {final_config.get('validation_threshold')}")
    print(f"  guards = {[g['name'] for g in final_config.get('guards', [])]}")
    print(f"  s08 effort = {final_config.get('effort', {}).get('s08_decide')}")
    print(f"  max_retries = {final_config.get('max_retries')}")

    # FORGE success criteria (falsifiable).
    assert jf > j0, "loop did not improve the benchmark"
    assert promotes, "no promotion occurred"
    assert all(c.validator_agreement for c in commits), "a move bypassed the cross-check validator"
    assert rollbacks, "inertia-brake never fired (expected at least one regressing candidate)"
    print("\nOK — all FORGE success criteria met.")


if __name__ == "__main__":
    main()
