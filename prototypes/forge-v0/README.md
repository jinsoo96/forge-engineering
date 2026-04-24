# forge-v0 — Minimum Working Forge

> Reference implementation of the dual-loop Forge architecture.
>
> Scope: Furnace + Hammer + Rewriter + Inertia Brake loop over a single repository. Skill Anvil / Prompt Tempering / Tool Smithing / Meta-agent are disabled in v0.

---

## Install (planned)

```bash
pip install -e .
forge --help
```

## Directory layout

```
forge-v0/
├── cli.py                 # forge init | watch | log | rollback
├── runner/
│   └── runner.py          # Inner Loop — wraps Claude Code task execution
├── smith/
│   ├── furnace.py         # trace intake + classification
│   ├── hammer.py          # Reflection JSON generator
│   └── rewriter.py        # Rewrite Proposal → git branch → PR
├── safety/
│   └── inertia_brake.py   # J(H_new) vs J(H_old) diff + auto-rollback
├── schemas/
│   ├── reflection.v1.json
│   ├── rewrite.v1.json
│   └── run.v1.json
├── bench/
│   └── fixed/lite.yaml    # external anchor — Smith cannot write here
└── demo/
    ├── scenario.md        # 10-run walkthrough
    ├── CLAUDE.md.initial
    └── sample_task.md
```

## Architectural invariants (inherited from FORGE.md)

- Runner and Smith run in **separate OS processes**. Runner has no write access to `CLAUDE.md` or `skills/`.
- Every harness commit carries `Derived-From-Reflection: <run_id>` trailer.
- `bench/fixed/` is mounted read-only to Smith.
- Reflection JSON must validate against `schemas/reflection.v1.json` before Rewriter is invoked.

## Success criterion

Run the demo scenario (`demo/scenario.md`) and observe:
1. Run 1 fails on a specific sub-task.
2. Smith generates a reflection naming the root cause.
3. CLAUDE.md gains a single line that encodes the lesson.
4. Run 2 of the same sub-task succeeds with fewer tool calls.
5. Benchmark improvement is recorded in `forge/commits.jsonl`.

If any of these fails, the prototype is not Forge-compliant.
