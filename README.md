# stock-quant-harness

Offline-first A-share quantitative research harness. The repository is in its
bootstrap phase; no market-data, brokerage, or live-execution integration is
implemented.

## Development setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
```
