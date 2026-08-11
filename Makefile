VENV ?= .venv
PYTHON ?= $(VENV)/bin/python
SYSTEM_PYTHON ?= python3
NODE ?= node

.PHONY: setup lint-md lint-python test validate hygiene check

setup:
	$(SYSTEM_PYTHON) scripts/setup_dev.py

lint-md:
	$(NODE) node_modules/markdownlint-cli2/markdownlint-cli2-bin.mjs

lint-python:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

test:
	$(PYTHON) -m unittest discover -s tests -v

validate:
	$(PYTHON) scripts/validate_repository.py

hygiene:
	$(PYTHON) scripts/public_hygiene_check.py

check:
	$(PYTHON) scripts/check.py
