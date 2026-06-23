"""Runner — config + task -> RunRecord. Same contract for mock and real engine.

MockRunner scores a HarnessConfig by distance to a hidden healthy profile and
emits *trace signals* that correlate with each deficiency. The reflector reads
ONLY the signals (never the hidden profile) — so diagnosis is trace-driven and
honest, exactly the L2(diagnosis) -> L4(evolution) flow we want to demonstrate.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class RunRecord:
    task_id: str
    score: float                       # [0,1]  — answer quality
    outcome: str                       # success | partial | failure
    signals: dict[str, float] = field(default_factory=dict)   # symptom -> magnitude
    cost: float = 0.0                  # [0,~1] — relative spend (effort/retries/iterations)


# Relative per-run spend of each judge-stage effort tier — lets the multi-objective
# optimizer trade quality against cost instead of pretending high effort lowers quality.
_EFFORT_COST = {"low": 0.0, "medium": 0.10, "high": 0.25, "xhigh": 0.60, "max": 1.0}


class Runner(Protocol):
    def run(self, config: dict[str, Any], task: dict[str, Any]) -> RunRecord: ...


def _seeded_noise(task_id: str, magnitude: float = 0.02) -> float:
    """Deterministic per-task jitter (no Math.random) so runs are reproducible."""
    h = int(hashlib.sha1(task_id.encode()).hexdigest()[:8], 16)
    return ((h % 1000) / 1000.0 - 0.5) * 2 * magnitude


class MockRunner:
    """Offline scorer. The hidden healthy profile is what the loop must discover."""

    def run(self, config: dict[str, Any], task: dict[str, Any]) -> RunRecord:
        score = 1.0
        sig: dict[str, float] = {}
        regulated = task.get("regulated", False)

        # 1) Judge must be enabled, else low-quality answers ship ungated.
        eval_strat = config.get("active_strategies", {}).get("s08_decide:evaluation", "none")
        if eval_strat in ("none", "rule_based"):
            score -= 0.30
            sig["ungated_low_quality"] = 1.0

        # 2) validation_threshold should sit near 0.8 (too low ships borderline; too high stalls).
        thr = config.get("validation_threshold", 0.5)
        if thr < 0.7:
            score -= 0.18 * (0.7 - thr) / 0.2
            sig["accepted_borderline"] = (0.7 - thr) / 0.2
        elif thr > 0.85:
            score -= 0.15 * (thr - 0.85) / 0.05
            sig["over_strict_stall"] = (thr - 0.85) / 0.05

        # 3) Regulated tasks need a content guard, else a regulation violation slips through.
        has_content_guard = any(g["name"] == "content" for g in config.get("guards", []))
        if regulated and not has_content_guard:
            score -= 0.25
            sig["regulation_violation"] = 1.0

        # 4) Judge stage effort: below 'high' is shallow; 'xhigh' over-spends for no extra gain.
        s08_effort = config.get("effort", {}).get("s08_decide", "medium")
        if s08_effort in ("low", "medium"):
            score -= 0.08
            sig["shallow_eval"] = 1.0
        elif s08_effort == "xhigh":
            score -= 0.10                      # silent cost: more effort than the task returns

        # 5) retries: 0 = no recovery; >2 = wasted loops.
        retries = config.get("max_retries", 1)
        if retries == 0:
            score -= 0.10
            sig["no_recovery"] = 1.0
        elif retries > 2:
            score -= 0.05
            sig["retry_waste"] = (retries - 2)

        score = max(0.0, min(1.0, score + _seeded_noise(task["id"])))
        outcome = "success" if score >= 0.85 else "partial" if score >= 0.6 else "failure"

        # relative spend — independent of quality; the multi-objective J penalizes it
        cost = (_EFFORT_COST.get(s08_effort, 0.10)
                + 0.05 * max(retries, 0)
                + 0.04 * max(config.get("max_iterations", 6) - 6, 0))
        return RunRecord(task_id=task["id"], score=round(score, 4), outcome=outcome,
                         signals=sig, cost=round(cost, 4))


class XgenHarnessRunner:
    """Phase 1 seam — drives the real engine. Stub until `xgen_harness` is wired."""

    def run(self, config: dict[str, Any], task: dict[str, Any]) -> RunRecord:
        raise NotImplementedError(
            "Phase 1: build a HarnessConfig from `config`, run the engine on task['input'], "
            "score = judge score vs task['expected']. Return RunRecord(score, outcome, signals)."
        )
