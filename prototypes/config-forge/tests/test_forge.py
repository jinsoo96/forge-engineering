"""Falsifiable tests for the forge loop — algebra, validator independence, and the
v2 optimizer's four properties (best-improvement, lookahead, ε-restore, cost-aware).

Synthetic runners make each scenario explicit, so the *algorithm* is tested in
isolation from the symptom tables; one end-to-end test drives the real bench."""
from algebra import Algebra, Move
from bench import BENCH
from demo import INITIAL_CONFIG
from forge import validator_ok
from runner import RunRecord, MockRunner
from search import objective, optimize


# ── tiny generic algebra over flat dict knobs (for the search-only tests) ──
class DictAlgebra:
    def apply(self, cfg, mv):
        c = dict(cfg)
        c[mv.target] = mv.value
        return c

    def inverse(self, cfg, mv):
        return Move(mv.op, mv.target, cfg.get(mv.target))

    def is_legal(self, mv):
        return True


_T = [{"id": "t"}]


def _rec(score, cost=0.0):
    return RunRecord(task_id="t", score=score, outcome="partial", cost=cost)


# ── real algebra: apply/inverse round-trips (deterministic rollback) ──
def test_algebra_inverse_roundtrip():
    alg = Algebra()
    cfg = {"validation_threshold": 0.5, "effort": {"s08_decide": "medium"}}
    for mv in [Move("tune_scalar", "validation_threshold", 0.8),
               Move("set_effort", "s08_decide", "high"),
               Move("toggle_guard", "content", True)]:
        after = alg.apply(cfg, mv)
        restored = alg.apply(after, alg.inverse(cfg, mv))
        assert restored.get("validation_threshold") == cfg.get("validation_threshold")
        assert restored.get("effort", {}).get("s08_decide") == cfg.get("effort", {}).get("s08_decide")
        assert [g["name"] for g in restored.get("guards", [])] == []


def test_validator_is_independent_and_on_target():
    alg = Algebra()
    # on-target move for the symptom -> agrees
    assert validator_ok("ungated_low_quality",
                        Move("set_strategy", "s08_decide:evaluation", "llm_judge"), alg)
    # a *legal* but off-target move for that symptom -> rejected (second opinion)
    assert not validator_ok("ungated_low_quality", Move("toggle_guard", "content", True), alg)
    # illegal value -> rejected
    assert not validator_ok("shallow_eval", Move("set_effort", "s08_decide", "ultra"), alg)


# ── best-improvement: pick the max-delta legal move, not the first ──
def test_best_improvement_picks_max_delta():
    class Bias:
        def run(self, cfg, task):
            return _rec(0.5 + (0.1 if cfg.get("a") else 0) + (0.3 if cfg.get("b") else 0))

    def propose(cfg):
        return [(f"set {k}", Move("set", k, True)) for k in ("a", "b") if not cfg.get(k)]

    best, hist, commits, J = optimize(Bias(), DictAlgebra(), _T, {}, propose=propose, depth=1)
    assert commits[0].move == "set(b=True)"        # took the bigger gain first
    assert best.get("a") and best.get("b") and J == 0.9


# ── lookahead: escape a local optimum a greedy step cannot ──
def test_lookahead_escapes_local_optimum():
    class Pair:
        # each knob alone is a slight regression; both together is a big win
        def run(self, cfg, task):
            n = int(bool(cfg.get("a"))) + int(bool(cfg.get("b")))
            return _rec({0: 0.5, 1: 0.47, 2: 1.0}[n])

    def propose(cfg):
        return [(f"set {k}", Move("set", k, True)) for k in ("a", "b") if not cfg.get(k)]

    # depth-1 greedy stalls at the start (no single positive move)
    _b1, _h1, _c1, J1 = optimize(Pair(), DictAlgebra(), _T, {}, propose=propose, depth=1, epsilon=0.05)
    assert J1 == 0.5
    # depth-2 lookahead crosses the lateral first step and reaches the global optimum
    b2, _h2, _c2, J2 = optimize(Pair(), DictAlgebra(), _T, {}, propose=propose, depth=2, epsilon=0.05)
    assert J2 == 1.0 and b2.get("a") and b2.get("b")


# ── ε-tolerant brake + best-seen restore: a regression never finalizes ──
def test_epsilon_best_seen_restore():
    class Drop:
        def run(self, cfg, task):
            return _rec(0.8 - (0.1 if cfg.get("x") else 0.0))

    def propose(cfg):
        return [] if cfg.get("x") else [("set x", Move("set", "x", True))]

    best, _hist, commits, J = optimize(Drop(), DictAlgebra(), _T, {}, propose=propose,
                                       depth=1, epsilon=0.02)
    assert J == 0.8 and not best.get("x")           # the only move regresses -> start kept
    assert commits and commits[-1].verdict == "rolled_back"


# ── cost-aware objective: cheaper move wins at equal quality ──
def test_cost_aware_prefers_cheaper():
    class Eff:
        def run(self, cfg, task):
            # quality needs at least 'high' effort; 'high' and 'xhigh' give equal quality
            quality = 0.9 if cfg.get("effort") in ("high", "xhigh") else 0.6
            cost = {"high": 0.25, "xhigh": 0.60}.get(cfg.get("effort"), 0.1)
            return _rec(quality, cost=cost)

    def propose(cfg):
        if cfg.get("effort") in ("high", "xhigh"):
            return []
        return [("hi", Move("set", "effort", "high")), ("xhi", Move("set", "effort", "xhigh"))]

    best, _h, _c, _J = optimize(Eff(), DictAlgebra(), _T, {}, propose=propose,
                                depth=1, cost_lambda=0.1)
    assert best.get("effort") == "high"            # xhigh loses on J = quality − λ·cost


# ── end-to-end on the real bench: solves it, cost-aware avoids xhigh ──
def test_default_pipeline_solves_bench():
    runner, alg = MockRunner(), Algebra()
    j0 = objective(runner, INITIAL_CONFIG, BENCH, 0.05)
    best, _hist, commits, best_J = optimize(runner, alg, BENCH, INITIAL_CONFIG,
                                            depth=2, beam=4, epsilon=0.03, cost_lambda=0.05)
    assert best_J > j0
    assert best["active_strategies"]["s08_decide:evaluation"] == "llm_judge"
    assert best["effort"]["s08_decide"] == "high"         # cost-aware: not xhigh
    assert any(g["name"] == "content" for g in best["guards"])
    assert all(c.verdict in ("promoted", "rolled_back") for c in commits)
