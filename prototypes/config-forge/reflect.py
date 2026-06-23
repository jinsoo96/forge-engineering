"""Reflection — run traces -> root-cause lesson + ranked typed candidate moves.

Honest by construction: it reads only trace *signals* (symptoms), maps the
dominant symptom to candidate moves drawn from the Algebra vocabulary, and
ranks by signal magnitude. It never sees the runner's hidden profile.

Default reflector is heuristic (deterministic, offline). Swap in an LLM
reflector (reflection.v1 JSON) at Phase 4 without touching the loop.
"""
from __future__ import annotations

from dataclasses import dataclass

from algebra import Move
from runner import RunRecord


@dataclass
class Reflection:
    lesson: str
    dominant_symptom: str
    candidates: list[Move]            # ranked; loop tries each, brake prunes empirically


# symptom -> (lesson, ordered candidate moves). Each move is type-checked by Algebra later.
# The shortlist hedges across the discretized neighborhood; Inertia-Brake decides the winner.
_SYMPTOM_FIXES: dict[str, tuple[str, list[Move]]] = {
    "ungated_low_quality": (
        "answers ship without isolated judging -> enable the LLM judge",
        [Move("set_strategy", "s08_decide:evaluation", "llm_judge")],
    ),
    "regulation_violation": (
        "regulated tasks lack a deterministic content gate -> add the content guard",
        [Move("toggle_guard", "content", True)],
    ),
    "accepted_borderline": (
        "validation threshold too low -> borderline answers accepted",
        [Move("tune_scalar", "validation_threshold", 0.8),
         Move("tune_scalar", "validation_threshold", 0.7)],
    ),
    "over_strict_stall": (
        "validation threshold too high -> retries stall on self-judge",
        [Move("tune_scalar", "validation_threshold", 0.8),
         Move("tune_scalar", "validation_threshold", 0.9)],   # 0.9 is the exploratory hedge -> brake rejects
    ),
    "shallow_eval": (
        "judge stage under-powered -> raise effort to high",
        [Move("set_effort", "s08_decide", "xhigh"),            # xhigh over-spends -> brake may reject
         Move("set_effort", "s08_decide", "high")],
    ),
    "no_recovery": (
        "no retry budget -> a single bad turn is terminal",
        [Move("tune_scalar", "max_retries", 2)],
    ),
    "retry_waste": (
        "too many retries -> wasted loops",
        [Move("tune_scalar", "max_retries", 2)],
    ),
}


def reflect(traces: list[RunRecord]) -> Reflection | None:
    """Aggregate symptom magnitude over failing/partial runs; diagnose the dominant one."""
    agg: dict[str, float] = {}
    for r in traces:
        if r.outcome == "success":
            continue
        for sym, mag in r.signals.items():
            agg[sym] = agg.get(sym, 0.0) + mag
    agg = {k: v for k, v in agg.items() if k in _SYMPTOM_FIXES and v > 0}
    if not agg:
        return None

    dominant = max(agg, key=agg.get)
    lesson, candidates = _SYMPTOM_FIXES[dominant]
    return Reflection(lesson=lesson, dominant_symptom=dominant, candidates=list(candidates))


def all_candidates(traces: list[RunRecord]) -> list[tuple[str, str, Move]]:
    """Every (symptom, lesson, move) for ALL active symptoms, ordered by magnitude.

    The single-symptom ``reflect`` drives the greedy v1 loop; the v2 optimizer needs
    the whole validated neighbourhood (across symptoms) to do best-improvement and
    lookahead. Still honest: derived only from trace signals."""
    agg: dict[str, float] = {}
    for r in traces:
        if r.outcome == "success":
            continue
        for sym, mag in r.signals.items():
            agg[sym] = agg.get(sym, 0.0) + mag
    out: list[tuple[str, str, Move]] = []
    for sym in sorted((s for s in agg if s in _SYMPTOM_FIXES and agg[s] > 0), key=lambda s: -agg[s]):
        lesson, moves = _SYMPTOM_FIXES[sym]
        out.extend((sym, lesson, mv) for mv in moves)
    return out
