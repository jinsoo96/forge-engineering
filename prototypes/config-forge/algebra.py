"""Substitution Algebra — the legal-move space over a typed HarnessConfig.

Every move is discovered from an injected primitive *registry* (mirrors the
engine's entry_points vocabulary) and is type-checked before it can be applied.
Moves compose and each has an inverse, so Inertia-Brake rollback is deterministic.

The registry is injected (not imported from the engine) so the PoC runs offline;
Phase 1 swaps it for `xgen_harness` registry listings with zero change here.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Move:
    op: str           # set_strategy | toggle_guard | set_effort | tune_scalar | edit_criterion | set_orchestrator
    target: str       # the knob this move addresses (stage / guard name / scalar key / criterion / stage:slot)
    value: Any        # new value (op-specific)

    def __str__(self) -> str:
        return f"{self.op}({self.target}={self.value!r})"


# Mirrors the engine's registered primitive vocabulary. Injected, not hardcoded logic.
DEFAULT_REGISTRY: dict[str, Any] = {
    "strategies": {                       # xgen_harness.strategies — (stage:slot) -> impls
        "s08_decide:evaluation": ["none", "rule_based", "llm_judge"],
        "s08_decide:decide": ["threshold", "always_pass"],
        "s06_context:compactor": ["token_budget", "cascade", "microcompact"],
    },
    "guards": {                           # xgen_harness.guards — name -> param schema (floor/ceiling only)
        "content": {"hard_block": [False, True]},
        "token_budget": {},
        "tool_diversity": {"max_repeats": [2, 3, 4]},
    },
    "scalars": {                          # runtime_defaults floor/ceiling
        "validation_threshold": {"choices": [0.5, 0.6, 0.7, 0.8, 0.9]},
        "max_retries": {"choices": [0, 1, 2, 3]},
        "max_iterations": {"choices": [4, 6, 8]},
    },
    "criteria": ["relevance", "completeness", "accuracy", "regulation"],
    "effort_levels": ["low", "medium", "high", "xhigh"],
    "effort_stages": ["s06_context", "s07_act", "s08_decide"],
}


class Algebra:
    def __init__(self, registry: dict[str, Any] | None = None) -> None:
        self.reg = registry or copy.deepcopy(DEFAULT_REGISTRY)

    # ---- generation -------------------------------------------------------
    def legal_moves(self, config: dict[str, Any]) -> list[Move]:
        """Every type-checked single-knob mutation reachable from `config`."""
        moves: list[Move] = []

        for slot, impls in self.reg["strategies"].items():
            cur = config.get("active_strategies", {}).get(slot)
            moves += [Move("set_strategy", slot, impl) for impl in impls if impl != cur]

        present = {g["name"] for g in config.get("guards", [])}
        for name in self.reg["guards"]:
            if name in present:
                moves.append(Move("toggle_guard", name, False))
            else:
                moves.append(Move("toggle_guard", name, True))

        for key, spec in self.reg["scalars"].items():
            cur = config.get(key)
            moves += [Move("tune_scalar", key, v) for v in spec["choices"] if v != cur]

        for stage in self.reg["effort_stages"]:
            cur = config.get("effort", {}).get(stage)
            moves += [Move("set_effort", stage, lvl) for lvl in self.reg["effort_levels"] if lvl != cur]

        active_crit = {c["name"] for c in config.get("criteria", [])}
        for name in self.reg["criteria"]:
            if name not in active_crit:
                moves.append(Move("edit_criterion", name, {"weight": 1.0, "hard": False}))
            else:
                moves.append(Move("edit_criterion", name, {"hard": True}))
        return moves

    def is_legal(self, move: Move) -> bool:
        if move.op == "set_strategy":
            return move.value in self.reg["strategies"].get(move.target, [])
        if move.op == "toggle_guard":
            return move.target in self.reg["guards"] and isinstance(move.value, bool)
        if move.op == "tune_scalar":
            return move.value in self.reg["scalars"].get(move.target, {}).get("choices", [])
        if move.op == "set_effort":
            return move.target in self.reg["effort_stages"] and move.value in self.reg["effort_levels"]
        if move.op == "edit_criterion":
            return move.target in self.reg["criteria"]
        return False

    # ---- application / inversion -----------------------------------------
    def apply(self, config: dict[str, Any], move: Move) -> dict[str, Any]:
        if not self.is_legal(move):
            raise ValueError(f"illegal move: {move}")
        c = copy.deepcopy(config)
        if move.op == "set_strategy":
            c.setdefault("active_strategies", {})[move.target] = move.value
        elif move.op == "toggle_guard":
            guards = [g for g in c.get("guards", []) if g["name"] != move.target]
            if move.value:
                guards.append({"name": move.target, "params": {}})
            c["guards"] = guards
        elif move.op == "tune_scalar":
            c[move.target] = move.value
        elif move.op == "set_effort":
            c.setdefault("effort", {})[move.target] = move.value
        elif move.op == "edit_criterion":
            crit = [dict(x) for x in c.get("criteria", [])]
            existing = next((x for x in crit if x["name"] == move.target), None)
            if existing:
                existing.update(move.value)
            else:
                crit.append({"name": move.target, **move.value})
            c["criteria"] = crit
        return c

    def inverse(self, config_before: dict[str, Any], move: Move) -> Move:
        """The move that restores `config_before` (computed from the pre-state)."""
        if move.op == "set_strategy":
            prev = config_before.get("active_strategies", {}).get(move.target, "none")
            return Move("set_strategy", move.target, prev)
        if move.op == "toggle_guard":
            was_present = any(g["name"] == move.target for g in config_before.get("guards", []))
            return Move("toggle_guard", move.target, was_present)
        if move.op == "tune_scalar":
            return Move("tune_scalar", move.target, config_before.get(move.target))
        if move.op == "set_effort":
            return Move("set_effort", move.target, config_before.get("effort", {}).get(move.target, "high"))
        if move.op == "edit_criterion":
            existing = next((x for x in config_before.get("criteria", []) if x["name"] == move.target), None)
            return Move("edit_criterion", move.target, dict(existing) if existing else {"weight": 0.0, "hard": False})
        raise ValueError(move.op)
