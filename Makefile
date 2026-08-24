PYTHON ?= .venv/bin/python

.PHONY: test eval lint type verify

test:
	$(PYTHON) -m pytest tests

eval:
	$(PYTHON) -m pytest evals

lint:
	$(PYTHON) -m ruff check .

type:
	$(PYTHON) -m mypy

verify: lint type test eval
