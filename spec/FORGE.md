# FORGE.md — Forge Engineering Compliance Declaration

> **Spec version: 0.1 (draft, 2026-04-24)**
>
> This file declares how a Forge-compliant runtime may evolve this repository's harness. It is the compilation target of Forge Engineering: AGENTS.md describes the harness; FORGE.md describes *how the harness is allowed to change*.
>
> A runtime without a valid FORGE.md must treat this repo as Harness-Engineering-only (read-only harness).

---

## 0. Relationship to AGENTS.md

```
AGENTS.md  →  static harness declaration  (what the agent knows)
FORGE.md   →  dynamic harness contract    (what the agent may rewrite)
```

FORGE.md strictly extends AGENTS.md. If AGENTS.md is absent, FORGE.md MUST NOT be interpreted.

---

## 1. Minimum declaration

A Forge-compliant repo MUST declare these fields.

```yaml
forge_version: "0.1"

agent:
  base_harness: AGENTS.md          # or CLAUDE.md
  runner_model: claude-opus-4-7
  smith_model: claude-opus-4-7
  validator_model: claude-sonnet-4-6   # must differ from smith_model

writable_surface:                  # what Smith may rewrite
  - path: CLAUDE.md
    mode: section-diff             # append-only | section-diff | full-rewrite
    owner: harness_rewrite
  - path: skills/
    mode: create-file
    owner: skill_anvil
  - path: tools/
    mode: create-file
    owner: tool_smithing

locked_surface:                    # Smith MUST NOT write here
  - path: FORGE.md
    reason: meta-stability
  - path: bench/fixed/
    reason: benchmark-hacking prevention
  - path: ontology/core.ttl
    reason: symbolic invariants
  - path: .env
    reason: secrets

mechanisms:
  furnace:             { enabled: true }
  reflection_hammer:   { enabled: true, schema: schemas/reflection.v1.json }
  skill_anvil:         { enabled: true,  trigger: "success_streak >= 3" }
  prompt_tempering:    { enabled: false, reason: "phase 2" }
  tool_smithing:       { enabled: true,  trigger: "adhoc_repeat >= 3" }
  harness_rewrite:     { enabled: true,  mode: local-only }
  meta_agent_archive:  { enabled: false, reason: "phase 3" }

safety:
  inertia_brake:
    benchmark: bench/fixed/lite.yaml
    threshold_delta: -0.05          # J_new - J_old; if below, auto-rollback
    on_violation: auto_rollback
    rollback_feeds_furnace: true    # the rollback event becomes learning fuel
  cross_check:
    required: true
    must_differ_from_smith: true
    agreement_rule: unanimous       # unanimous | majority
  ontology_gate:
    file: ontology/core.ttl
    on_violation: reject_proposal

observability:
  run_log: runs/                    # append-only trace store
  forge_log: forge/commits.jsonl    # every harness commit
  audit_tag_required: true          # every forge commit must carry Derived-From-Reflection trailer

schemas:
  reflection: schemas/reflection.v1.json
  rewrite:    schemas/rewrite.v1.json
  run:        schemas/run.v1.json
```

---

## 2. Required guarantees (a compliant runtime MUST enforce)

1. **Isolation.** Runner process has NO write access to any path in `writable_surface` or `locked_surface`. Only Smith writes; only through branch + PR.
2. **Audit.** Every harness-write commit message MUST contain `Derived-From-Reflection: <run_id>` trailer. A commit without it is rejected.
3. **Rollback-first.** When `inertia_brake.threshold_delta` is violated, the runtime MUST auto-revert BEFORE continuing. No "try again" loop around a failed commit.
4. **External anchor.** `bench/fixed/` files are mounted read-only to Smith's filesystem view. A runtime that cannot enforce this SHALL refuse to load FORGE.md.
5. **Schema conformance.** Any JSON written to `runs/` / `forge/commits.jsonl` MUST validate against the declared schemas. Non-validating data is discarded and logged.
6. **Ontology gate.** If `ontology_gate.file` is present, every rewrite proposal runs through the ontology's validator (SPARQL / OWL reasoner) before merge.

---

## 3. Commit message format (mandatory)

```
forge(<mechanism>): <one-line change>

Derived-From-Reflection: <run_id>
Lesson: <≤3 lines>
Benchmark-Before: J=<float>  on <bench_file>
Benchmark-After:  J=<float>  on <bench_file>
Rollback-If: <condition>
Validator-Agreement: yes | no
Ontology-Check: pass | fail
```

Missing any field ⇒ commit rejected by pre-receive hook.

---

## 4. Mechanism-level sub-specs

### 4.1 Harness Rewrite modes
- `local-only` — Smith may only diff existing sections of writable P files. No new top-level sections.
- `section-add` — Smith may add new sections (requires Validator unanimous).
- `full-rewrite` — Smith may replace entire file (requires HITL approval; not recommended for v0.1).

### 4.2 Skill Anvil trigger grammar
```
trigger: "<predicate>"
```
Predicates available in v0.1:
- `success_streak >= N`
- `distinct_tasks_with_pattern >= N`
- `cost_saving_estimate >= X`

### 4.3 Tool Smithing trigger grammar
- `adhoc_repeat >= N` — same external call observed N times
- `token_cost_of_pattern >= X` — cumulative cost

### 4.4 Meta-agent archive (disabled in v0.1)
When enabled in Phase 3, an additional top-level `meta_agent:` section will declare:
- archive storage path
- weekly batch cadence
- A/B benchmark set (distinct from `bench/fixed/lite.yaml`)

---

## 5. Degraded modes

- **No ontology file present.** Ontology gate silently disabled, but runtime MUST log a warning on every commit. Recommended for greenfield projects only.
- **No validator model available.** Cross-check disabled ⇒ `mechanisms.harness_rewrite.mode` SHALL be downgraded to `local-only` and HITL required.
- **Benchmark file missing.** Inertia brake cannot fire ⇒ `safety.inertia_brake` auto-set to `on_violation: refuse_all_writes` (Smith becomes read-only until fixed).

---

## 6. Versioning

- `forge_version: "0.1"` pins spec. Forward-incompatible changes require major bump.
- Runtimes MUST refuse to load a FORGE.md with a higher `forge_version` than they support.

---

## 7. Reference implementation

See `prototypes/forge-v0/` in this repo.
