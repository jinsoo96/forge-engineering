# sample_app — Forge demonstrator

A deliberately buggy Python library used to exercise the Forge loop end-to-end.
The Runner attempts to make `pytest` pass; the Smith evolves `CLAUDE.md` from
the trace of what went wrong.

```
src/sample_app/numbers.py   # 3 functions, 2 of which contain bugs
tests/test_numbers.py       # 6 tests; 2 fail against the shipped buggy code
```

Run the tests directly:

```bash
cd demo/sample_repo
pip install -e .
pytest
```
