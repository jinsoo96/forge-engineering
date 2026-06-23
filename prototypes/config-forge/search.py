"""Forge loop v2 — a plateau-aware lookahead optimizer over the typed HarnessConfig.

forge.py is greedy first-improvement: it takes the first validated move with a
positive delta and re-reflects. That cannot:
  * pick the *best* of several legal moves (it takes the first positive one),
  * cross a plateau / escape a local optimum (it only ever steps strictly uphill),
  * avoid re-trying a move it already walked back (no memory),
  * reason about *cost*, only quality.

This optimizer fixes all four while keeping every honesty guarantee of v1:

  * **best-improvement** — evaluates the whole validated neighbourhood, keeps the best.
  * **depth-D lookahead (beam)** — scores a move by the best benchmark reachable D
    steps out, so a flat/slightly-negative first move that *unlocks* a bigger gain is
    taken (local-optimum escape). `depth=1` degrades to best-improvement greedy.
  * **ε-tolerant inertia brake + best-seen restore** — a lateral first move (Δ ≥ −ε)
    is allowed when the horizon improves; the best config ever seen is always what's
    returned, so exploration can never finalize a regression.
  * **tabu memory** — a move once applied/rejected is never re-proposed (no cycles).
  * **cost-aware objective** — J = mean(quality) − λ·mean(cost), so over-spend
    (e.g. `xhigh` effort) loses on the objective itself, not via a faked quality drop.

The search talks to the world only through a ``propose(config) -> [(reason, Move)]``
seam (default = the trace-driven reflect + independent validator pipeline), so the
algorithm is testable in isolation from the symptom tables.
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from algebra import Algebra, Move
from forge import validator_ok
from reflect import all_candidates
from runner import Runner

COMMITS_LOG = Path.cwd() / "forge" / "commits_v2.jsonl"

Proposer = Callable[[dict[str, Any]], "list[tuple[str, Move]]"]


@dataclass
class OptCommit:
    step: int
    reason: str
    move: str
    inverse: str
    bench_before: float
    bench_after: float       # immediate J after the first move
    horizon: float           # best J reachable within the lookahead
    delta: float
    verdict: str             # promoted | rolled_back


def _key(m: Move) -> tuple:
    return (m.op, m.target, repr(m.value))


def objective(runner: Runner, config: dict[str, Any], bench: list[dict[str, Any]],
              cost_lambda: float = 0.0) -> float:
    """J = mean(quality) − λ·mean(cost). λ=0 reproduces the pure-quality v1 anchor."""
    recs = [runner.run(config, t) for t in bench]
    q = sum(r.score for r in recs) / len(recs)
    c = sum(getattr(r, "cost", 0.0) for r in recs) / len(recs)
    return round(q - cost_lambda * c, 4)


def default_proposer(runner: Runner, bench: list[dict[str, Any]], algebra: Algebra) -> Proposer:
    """Trace-driven, validator-checked neighbourhood (honest: signals only)."""
    def propose(config: dict[str, Any]) -> list[tuple[str, Move]]:
        traces = [runner.run(config, t) for t in bench]
        out: list[tuple[str, Move]] = []
        for sym, lesson, mv in all_candidates(traces):
            if validator_ok(sym, mv, algebra):
                out.append((f"{sym}: {lesson}", mv))
        return out
    return propose


def _plan(config, runner, bench, algebra, propose, depth, beam, cost_lambda, tabu):
    """Return (first_move, immediate_J, horizon_J, reason) maximizing J over ≤depth plies."""
    cands = [(r, m) for (r, m) in propose(config) if _key(m) not in tabu]
    if not cands:
        return None
    scored = []
    for reason, mv in cands:
        child = algebra.apply(config, mv)
        scored.append((objective(runner, child, bench, cost_lambda), reason, mv, child))
    scored.sort(key=lambda x: -x[0])

    if depth <= 1:
        jc, reason, mv, _child = scored[0]
        return (mv, jc, jc, reason)

    best = None
    for jc, reason, mv, child in scored[:beam]:
        sub = _plan(child, runner, bench, algebra, propose, depth - 1, beam,
                    cost_lambda, tabu | {_key(mv)})
        horizon = sub[2] if sub else jc
        if best is None or horizon > best[2]:
            best = (mv, jc, horizon, reason)
    return best


def optimize(
    runner: Runner,
    algebra: Algebra,
    bench: list[dict[str, Any]],
    config: dict[str, Any],
    *,
    propose: Proposer | None = None,
    depth: int = 2,
    beam: int = 4,
    epsilon: float = 0.02,
    patience: int = 2,
    cost_lambda: float = 0.0,
    max_steps: int = 24,
    write_log: bool = False,
) -> tuple[dict[str, Any], list[float], list[OptCommit], float]:
    """Returns (best_config, J-history, commits, best_J)."""
    propose = propose or default_proposer(runner, bench, algebra)
    cur = copy.deepcopy(config)
    cur_J = objective(runner, cur, bench, cost_lambda)
    best_config, best_J = copy.deepcopy(cur), cur_J
    history = [cur_J]
    commits: list[OptCommit] = []
    tabu: set[tuple] = set()
    no_improve = 0

    for step in range(max_steps):
        plan = _plan(cur, runner, bench, algebra, propose, depth, beam, cost_lambda, tabu)
        if plan is None:
            break
        mv, imm_J, horizon_J, reason = plan
        improves = horizon_J > cur_J + 1e-9          # a gain is reachable within the horizon
        not_a_drop = imm_J >= cur_J - epsilon         # first step is at worst a tolerated lateral
        verdict = "promoted" if (improves and not_a_drop) else "rolled_back"
        inv = algebra.inverse(cur, mv)
        commits.append(OptCommit(
            step=step, reason=reason, move=str(mv), inverse=str(inv),
            bench_before=cur_J, bench_after=imm_J, horizon=round(horizon_J, 4),
            delta=round(imm_J - cur_J, 4), verdict=verdict,
        ))
        tabu.add(_key(mv))                            # never re-walk this move
        if verdict != "promoted":
            break                                     # best reachable plan regresses -> converged
        cur, cur_J = algebra.apply(cur, mv), imm_J
        history.append(cur_J)
        if cur_J > best_J + 1e-9:
            best_config, best_J, no_improve = copy.deepcopy(cur), cur_J, 0
        else:
            no_improve += 1                           # lateral step: explored, no new best
            if no_improve >= patience:
                break

    if write_log:
        _write_log(commits)
    return best_config, history, commits, best_J


def _write_log(commits: list[OptCommit]) -> None:
    COMMITS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with COMMITS_LOG.open("w", encoding="utf-8") as f:
        for c in commits:
            f.write(json.dumps(c.__dict__, ensure_ascii=False) + "\n")
