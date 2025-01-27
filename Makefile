VENV = .venv
PYTHON = $(VENV)/bin/python

.PHONY: venv test clean

venv:
	python3 -m venv $(VENV)
	$(PYTHON) -m pip install -q --upgrade pip setuptools wheel
	$(PYTHON) -m pip install -e .[dev]

test:
	$(PYTHON) -m pytest -v --cov=src --cov-report=term-missing tests/

clean:
	rm -rf $(VENV) .coverage .pytest_cache build dist *.egg-info 