# Forge Engineering

> A meta-engineering discipline above Harness Engineering. Agents that rewrite their own harness under versioned, observable, benchmark-gated control.

**Started:** 2026-04-24.
**Status:** Theory + spec + prototype skeleton.
**Author:** Jinsoo Kim (<wlstn010203@gmail.com>) · GitHub [@jinsoo96](https://github.com/jinsoo96)

---

## TL;DR

Prompt Engineering tuned one sentence.
Context Engineering assembled a briefing.
Harness Engineering built the workbench.
**Forge Engineering designs the workbench that rebuilds itself — and proves it won't diverge.**

Forge is not a new harness. It is a theory *of* harness evolution.

---

## Why this exists

In February 2026 Mitchell Hashimoto named **Harness Engineering**, and OpenAI's Ryan Lopopolo popularized it a week later. Within two months, every major vendor (Anthropic, OpenAI, Google, Microsoft, Red Hat) had published on it. Harness engineering became the accepted way to build agents.

But harnesses — AGENTS.md, CLAUDE.md, tool specs, permission policies — are **static artifacts maintained by humans**. Current practice has documented limits:

1. Markdown rot: rules drift from code, becoming "attractive nuisance."
2. 65% of enterprise AI failures trace to harness-level data defects (Masood, 2026).
3. Orientation tax: agents burn tokens exploring unmapped environments.
4. Self-evaluation weakness: agents confidently praise mediocre work.
5. Token-cost ceiling: $124–200 and 4–6 hours per agent build.
6. Behavior verification gap: tools check maintainability, not intent fulfillment.
7. Multi-agent brittleness: production converges back to bounded, deterministic workflows.

Harnesses answer "how do I configure one agent run." They do not answer "how do I configure an agent that gets better at configuring itself." That is the Forge question.

---

## What Forge does

### 1. Types the harness as an algebraic structure
```
H = (P, T, W, M, G, C)
```
where P=prompts, T=tools, W=workflows, M=memory, G=guards, C=ontology constraints.

### 2. Defines Forge as an operator on harness-space
```
F : 𝓗 × Evidence → 𝓗
```
Every execution yields evidence. Every batch of evidence produces a harness commit. Forge is the endofunctor.

### 3. Names and defends against Stochastic Inertia
Self-modifying agents drift into *"directions they believe are right but aren't."* Forge specifies a four-tier defense:

| Tier | Mechanism | Guarantee |
|------|-----------|-----------|
| Structural | Runner/Smith process separation | Runner cannot self-modify |
| Symbolic | Ontology constraint gate | Rewrites violating invariants rejected |
| Deterministic | Inertia Brake (benchmark -5% ⇒ rollback) | V(H_n) monotonically non-increasing |
| Stochastic | Cross-Check Validator (independent model) | Bounds systematic bias propagation |

Together they yield **conditional Lyapunov stability** (see `docs/04-theory.md §6`).

### 4. Integrates symbolic constraints with neural self-evolution
Ontology (OWL/RDF) enforces hard invariants; self-evolution operates within that feasible subspace. No existing self-improving framework ships this integration.

---

## Dual-Loop architecture

```
      🏃 Runner (Inner)                       ⚒️ Smith (Outer)
      ─ executes user task                    ─ observes, analyzes, rewrites harness
      ─ cannot self-modify                    ─ cannot execute user tasks
                 ↓                                    ↑
                 └───── trace / metrics ──────────────┘
                                ↓
                        🧠 Ontology Gate
                                ↓
                        🛡 Safety Harness
                                ↓
                        📜 Versioned Harness Store
```

Smith runs six mechanisms:
- 🔥 **Failure Furnace** — trace collection & classification
- 🔨 **Reflection Hammer** — schema-structured verbal reflection (Reflexion)
- ⚒️ **Skill Anvil** — skill-library-as-code (Voyager)
- 🌡 **Prompt Tempering** — textual gradient + self-referential mutation (TextGrad + Promptbreeder)
- 🛠 **Tool Smithing** — closed-loop self-correcting tool generation (ToolMaker/CREATOR/LATM)
- 📜 **Harness Rewrite** — meta-agent archive search (ADAS)

Two of these — self-referential mutation and meta-agent archive — are identified gaps not yet integrated in any existing framework.

---

## What's here

```
forge-engineering/
├── README.md              ← you are here
├── docs/
│   ├── 00-manifesto.md    ← 5 principles + Harness limits mapping
│   ├── 01-definition.md   ← glossary + Reflection/Rewrite JSON schemas
│   ├── 02-architecture.md ← dual-loop + 6 mechanisms + ontology + inertia defense
│   ├── 03-roadmap.md      ← phased execution plan
│   └── 04-theory.md       ← formal theory: H, F, Lyapunov stability, convergence
├── spec/
│   └── FORGE.md           ← compliance declaration format (v0.1 draft)
├── research/
│   ├── harness-engineering.md
│   └── self-improving-agents.md
└── prototypes/
    └── forge-v0/          ← Minimum Working Forge skeleton
```

---

## Claim of priority

This repository is the **first public articulation** of Forge Engineering as a named discipline distinct from Harness Engineering, to the author's knowledge (2026-04-24). "ForgeCode" (a multi-agent harness product) and "Mistral Forge" (an AI model builder product) predate this work as *product names*; this work claims the *discipline name* at the layer above harness engineering.

First commit timestamp of this repo is the intended priority anchor. See git log.

---

## Intellectual lineage

Forge stands on prior work:

- **Reflexion** (Shinn 2023) — verbal reflection buffer
- **Voyager** (Wang 2023) — executable skill library
- **DSPy** (Khattab 2023) — declarative self-improving LM programs
- **TextGrad** (Yuksekgonul 2024) — natural-language backprop
- **Promptbreeder** (Fernando 2023) — self-referential prompt evolution
- **ADAS** (Hu 2025) — meta-agent archive search
- **Constitutional AI** (Anthropic 2022) — critique-revise
- **Harness Engineering** (Hashimoto 2026-02, Lopopolo 2026-02-11) — the immediate predecessor discipline

Forge's contribution is not invention of a new mechanism. It is:
1. Formal typing of the harness.
2. Positioning self-evolution as operator dynamics.
3. Naming Stochastic Inertia and specifying its four-tier defense.
4. Defining FORGE.md as the declarative compilation target on top of AGENTS.md.

---

## License

MIT (planned for initial OSS release).

---

## Contact

Jinsoo Kim · <wlstn010203@gmail.com> · GitHub [@jinsoo96](https://github.com/jinsoo96)

Interested in collaboration, review, or constructive attack on the formalism? Open an issue.
