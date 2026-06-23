# config-forge — Self-Forging over a typed HarnessConfig (PoC)

> Phase-0 prototype for `spec/CONFIG-FORGE.md`. Upgrades forge-v0's loop from
> rewriting brittle markdown (CLAUDE.md) to **evolving a type-checked
> `HarnessConfig`** — choosing, per stage, which registered strategy / guard /
> effort / criterion to use — validated by an external benchmark J.
>
> Offline, no API, deterministic. The whole loop runs with a `MockRunner`; a
> `Runner` protocol leaves a zero-change seam to the real engine (Phase 1).

## Run

```bash
PYTHONUTF8=1 python demo.py     # Windows console: PYTHONUTF8=1 avoids cp949 errors
```

Expected: J climbs `0.318 -> 0.996`, one `xhigh` candidate is **rolled back** by
the inertia-brake (over-spend), `high` is promoted instead, and all moves pass
the cross-check validator. Audit trail at `forge/commits.jsonl`.

## What it demonstrates (vs forge-v0)

| forge-v0 | config-forge |
|---|---|
| writes CLAUDE.md (brittle markdown) | writes a **typed `HarnessConfig`** (stage→strategy/guard/effort/criteria) |
| smith = free-text line | smith = **substitution algebra** (only registered primitives, type-checked) |
| score = pytest pass rate | J = benchmark score (judge-quality proxy) |
| git revert rollback | deterministic **inverse move** rollback |

## Pieces

- `algebra.py` — `Move` + `Algebra`: discovers legal moves from an injected
  primitive registry (mirrors engine `entry_points`), `apply` / `inverse`.
- `runner.py` — `Runner` protocol; `MockRunner` (offline scorer emitting honest
  trace *signals*); `XgenHarnessRunner` (Phase-1 stub for the real engine).
- `reflect.py` — trace signals → root-cause lesson + ranked typed candidate moves
  (heuristic default; swap an LLM reflector at Phase 4).
- `forge.py` — the v1 loop: measure → reflect → propose → **cross-check validator
  (≠ reflector)** → **inertia-brake (empirical J)** → promote/rollback → audit.
- `search.py` — the **v2 optimizer** (see below): best-improvement + depth-D
  lookahead + ε-tolerant brake + best-seen restore + tabu + cost-aware J.
- `bench.py` — fixed external anchor (locked surface).
- `demo.py` / `demo_v2.py` — v1 and v2 walkthroughs + FORGE success-criteria asserts.
- `tests/` — falsifiable pytest for algebra inversion, validator independence, and
  each v2 property (best-improvement, lookahead escape, ε-restore, cost-aware).

## Honesty guarantees

- The reflector reads **only trace signals**, never the runner's hidden profile —
  diagnosis is trace-driven (the L2→L4 flow).
- The validator's symptom→move table is **independent** of the reflector's
  (cross_check, FORGE §2): a move is applied only if both agree it is legal,
  minimal, and addresses the diagnosed symptom.
- The inertia-brake decides empirically on J; reflection only *narrows* the move
  space, the benchmark *decides* (mirrors forge-v0 rewriter ↔ brake split).

## Forge loop v2 — lookahead, cost-aware optimizer (`search.py`)

v1 (`forge.py`) is greedy first-improvement: first validated move with Δ>0, then
re-reflect. v2 keeps every honesty guarantee but upgrades the *search*:

| limitation in v1 | v2 |
|---|---|
| takes the *first* positive move | **best-improvement** — scores the whole validated neighbourhood, keeps the max |
| only steps strictly uphill (stuck at local optima) | **depth-D lookahead (beam)** — scores a move by the best J reachable D steps out, so a flat/slightly-negative first move that *unlocks* a bigger gain is taken (`depth=1` ⇒ greedy best-improvement) |
| can re-try a walked-back move | **tabu memory** — a move once applied/rejected is never re-proposed |
| binary Δ>0; exploration can finalize a regression | **ε-tolerant inertia brake + best-seen restore** — lateral moves (Δ ≥ −ε) allowed when the horizon improves; the best config ever seen is always returned |
| objective = quality only | **cost-aware J = mean(quality) − λ·mean(cost)** — over-spend (e.g. `xhigh` effort) loses on the objective itself, not via a faked quality drop |

The optimizer talks to the world only through a `propose(config) → [(reason, Move)]`
seam (default = trace-driven reflect + independent validator), so the algorithm is
unit-tested in isolation from the symptom tables.

```bash
PYTHONUTF8=1 python demo_v2.py      # v2 vs greedy on the same bench
PYTHONUTF8=1 python -m pytest -q     # 7 falsifiable tests
```

Result: v2 reaches the same quality optimum as greedy in fewer, cleaner steps (no
wasted rollback), and the cost-aware objective selects `high` judge effort over
`xhigh`. Audit at `forge/commits_v2.jsonl` (each move tagged with the horizon it unlocks).

## Phase 1 (next)

Implement `XgenHarnessRunner.run(config, task)`: build a real `HarnessConfig`
from `config`, run the engine on `task["input"]`, set `score` = judge score vs
`task["expected"]`, populate `signals` from the engine's evaluation/guard events.
Replace the injected registry with `xgen_harness` registry listings. The loop,
algebra, reflector, and brake stay unchanged.
