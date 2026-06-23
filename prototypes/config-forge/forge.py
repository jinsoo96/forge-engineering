"""Self-Forging loop over a typed HarnessConfig.

measure(J) -> reflect(trace) -> propose typed move -> cross-check validator
-> Inertia-Brake (empirical J before/after) -> promote or rollback -> audit.

The loop only ever WRITES config knobs drawn from the Algebra (locked surface:
engine code / bench / criteria semantics are untouchable). J is the external
anchor; the validator is independent of the reflector (cross_check, FORGE §2).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from algebra import Algebra, Move
from reflect import Reflection, reflect
from runner import Runner

COMMITS_LOG = Path.cwd() / "forge" / "commits.jsonl"

# Independent cross-check: which (op, target) a given symptom legitimately maps to.
# Deliberately NOT the reflector's table — this is a second opinion.
_SYMPTOM_EXPECTED: dict[str, tuple[str, str]] = {
    "ungated_low_quality": ("set_strategy", "s08_decide:evaluation"),
    "regulation_violation": ("toggle_guard", "content"),
    "accepted_borderline": ("tune_scalar", "validation_threshold"),
    "over_strict_stall": ("tune_scalar", "validation_threshold"),
    "shallow_eval": ("set_effort", "s08_decide"),
    "no_recovery": ("tune_scalar", "max_retries"),
    "retry_waste": ("tune_scalar", "max_retries"),
}


@dataclass
class Commit:
    step: int
    reflection_id: str
    lesson: str
    move: str
    inverse: str
    bench_before: float
    bench_after: float
    delta: float
    validator_agreement: bool
    verdict: str            # promoted | rolled_back


def measure(runner: Runner, config: dict[str, Any], bench: list[dict[str, Any]]) -> float:
    return round(sum(runner.run(config, t).score for t in bench) / len(bench), 4)


def validator_ok(symptom: str, move: Move, algebra: Algebra) -> bool:
    """Independent cross-check for one (symptom, move): legal + minimal + addresses it.

    Uses the validator's OWN symptom->knob table (deliberately not the reflector's),
    so a move is applied only if a second opinion agrees it is legal and on-target."""
    if not algebra.is_legal(move):
        return False
    expected = _SYMPTOM_EXPECTED.get(symptom)
    return bool(expected) and (move.op, move.target) == expected


def validator_agrees(refl: Reflection, move: Move, algebra: Algebra) -> bool:
    """Cross-check for the greedy loop: legal + addresses the dominant symptom."""
    return validator_ok(refl.dominant_symptom, move, algebra)


def forge_loop(
    runner: Runner,
    algebra: Algebra,
    bench: list[dict[str, Any]],
    config: dict[str, Any],
    max_steps: int = 12,
) -> tuple[dict[str, Any], list[float], list[Commit]]:
    J = measure(runner, config, bench)
    history = [J]
    commits: list[Commit] = []

    for step in range(max_steps):
        traces = [runner.run(config, t) for t in bench]
        refl = reflect(traces)
        if refl is None:
            break                                  # no symptoms left -> converged

        progressed = False
        for move in refl.candidates:
            agree = validator_agrees(refl, move, algebra)
            if not agree:
                continue
            inv = algebra.inverse(config, move)     # deterministic rollback handle
            new_config = algebra.apply(config, move)
            J_new = measure(runner, new_config, bench)
            delta = round(J_new - J, 4)
            verdict = "promoted" if delta > 0 else "rolled_back"
            commits.append(Commit(
                step=step,
                reflection_id=f"r{step:02d}:{refl.dominant_symptom}",
                lesson=refl.lesson,
                move=str(move),
                inverse=str(inv),
                bench_before=J,
                bench_after=J_new,
                delta=delta,
                validator_agreement=agree,
                verdict=verdict,
            ))
            if verdict == "promoted":
                config, J = new_config, J_new
                history.append(J)
                progressed = True
                break                               # re-reflect from the improved state

        if not progressed:
            break                                   # best candidate regressed -> converged

    _write_log(commits)
    return config, history, commits


def _write_log(commits: list[Commit]) -> None:
    COMMITS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with COMMITS_LOG.open("w", encoding="utf-8") as f:
        for c in commits:
            f.write(json.dumps(c.__dict__, ensure_ascii=False) + "\n")
