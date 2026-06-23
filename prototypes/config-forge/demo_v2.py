"""Forge loop v2 walkthrough — the lookahead, cost-aware optimizer.

Runs the v2 `optimize` on the same bench + MockRunner as demo.py, alongside the
greedy v1 `forge_loop`, and shows:
  * best-improvement + depth-2 lookahead reach the same quality optimum,
  * the **cost-aware** objective (J = quality − λ·cost) makes the loop choose `high`
    judge effort over `xhigh` on the objective itself (no faked quality drop),
  * a richer audit (each move scored by the horizon it unlocks) at forge/commits_v2.jsonl.

Run:  PYTHONUTF8=1 python demo_v2.py        # offline, no API, deterministic
"""
from __future__ import annotations

from algebra import Algebra
from bench import BENCH
from demo import INITIAL_CONFIG
from forge import forge_loop
from runner import MockRunner
from search import objective, optimize

LAMBDA = 0.05   # cost weight in J = quality − λ·cost


def main() -> None:
    runner, algebra = MockRunner(), Algebra()

    # v1 greedy baseline (pure quality)
    _gcfg, g_hist, g_commits = forge_loop(runner, algebra, BENCH, INITIAL_CONFIG, max_steps=12)
    g_quality = g_hist[-1]

    # v2 optimizer: depth-2 lookahead, ε-tolerant brake, cost-aware
    j0 = objective(runner, INITIAL_CONFIG, BENCH, LAMBDA)
    best, hist, commits, best_J = optimize(
        runner, algebra, BENCH, INITIAL_CONFIG,
        depth=2, beam=4, epsilon=0.03, patience=2, cost_lambda=LAMBDA, write_log=True,
    )
    v2_quality = objective(runner, best, BENCH, 0.0)   # pure quality of the v2 result

    print("=" * 76)
    print("CONFIG-FORGE v2 — lookahead, cost-aware self-forging optimizer")
    print("=" * 76)
    print(f"objective: J = quality − {LAMBDA}·cost      (depth=2 lookahead, ε=0.03)")
    print(f"initial J = {j0:.4f}    final J = {best_J:.4f}    gain = +{best_J - j0:.4f}")
    print(f"J curve: {' -> '.join(f'{j:.3f}' for j in hist)}")
    print("-" * 76)
    print(f"{'step':>4} {'verdict':>11} {'delta':>7} {'horizon':>8}  move")
    for c in commits:
        print(f"{c.step:>4} {c.verdict:>11} {c.delta:>+7.4f} {c.horizon:>8.4f}  {c.move}")
        print(f"{'':>33}└ {c.reason}")
    print("-" * 76)
    print(f"v1 greedy  : steps={len(g_commits)}  final quality={g_quality:.4f}")
    print(f"v2 optimizer: steps={len(commits)}  final quality={v2_quality:.4f}  (cost-aware J={best_J:.4f})")
    print("final config knobs:")
    print(f"  evaluation strategy = {best['active_strategies'].get('s08_decide:evaluation')}")
    print(f"  validation_threshold = {best.get('validation_threshold')}")
    print(f"  guards = {[g['name'] for g in best.get('guards', [])]}")
    print(f"  s08 effort = {best.get('effort', {}).get('s08_decide')}   (cost-aware: not 'xhigh')")

    # falsifiable criteria
    assert best_J > j0, "optimizer did not improve the objective"
    assert v2_quality >= g_quality - 1e-9, "v2 quality regressed vs greedy"
    assert best["active_strategies"].get("s08_decide:evaluation") == "llm_judge"
    assert best.get("effort", {}).get("s08_decide") != "xhigh", "cost-aware J should reject xhigh"
    print("\nOK — v2 matches greedy quality, and the cost-aware objective rejects over-spend.")


if __name__ == "__main__":
    main()
