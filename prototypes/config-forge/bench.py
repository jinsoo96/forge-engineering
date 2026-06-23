"""External anchor — a tiny fixed benchmark. Locked surface: the smith may NOT
edit this (FORGE §2). In Phase 1 each task carries {input, expected} and J is
the judge score; here only ids + a `regulated` flag drive the MockRunner.
"""
from __future__ import annotations

BENCH: list[dict] = [
    {"id": "t01-summarize", "regulated": False},
    {"id": "t02-extract", "regulated": False},
    {"id": "t03-policy-qa", "regulated": True},
    {"id": "t04-refund-rule", "regulated": True},
    {"id": "t05-classify", "regulated": False},
    {"id": "t06-compliance", "regulated": True},
]
