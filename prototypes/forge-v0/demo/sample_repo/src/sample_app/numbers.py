"""Small numeric utilities.

Two of these functions ship with bugs. The failing tests in tests/ pin down
exactly which behavior is wrong.
"""
from __future__ import annotations

from typing import Iterable


def celsius_to_fahrenheit(c: float) -> float:
    return c * 9 / 5 + 32


def fahrenheit_to_celsius(f: float) -> float:
    # BUG: precedence wrong — should be (f - 32) * 5/9.
    return (f + 32) * 5 / 9


def running_mean(xs: Iterable[float]) -> list[float]:
    """Return the running mean of xs.

    For input [1, 2, 3] expected output is [1.0, 1.5, 2.0].
    """
    # BUG: divides by index instead of (index + 1); fails on first element.
    out: list[float] = []
    total = 0.0
    for i, x in enumerate(xs):
        total += x
        out.append(total / i if i else total)
    return out
