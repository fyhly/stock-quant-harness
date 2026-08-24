# stock-quant-harness

Offline-first A-share quantitative research harness. The repository is in its
bootstrap phase; no market-data, brokerage, or live-execution integration is
implemented.

## Development setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
make verify
```

`make test` runs the test suite, `make eval` runs executable acceptance
evaluations, and `make verify` aggregates lint, type checking, tests, and evals.
All commands are offline and return nonzero when a check fails.
