VENV ?= .venv
PYTHON ?= $(VENV)/bin/python
SYSTEM_PYTHON ?= python3

.PHONY: setup test validate hygiene check

setup:
	$(SYSTEM_PYTHON) scripts/setup_dev.py

test:
	$(PYTHON) -m unittest discover -s tests -v

validate:
	$(PYTHON) scripts/validate_repository.py

hygiene:
	$(PYTHON) scripts/public_hygiene_check.py

check:
	$(PYTHON) scripts/check.py
