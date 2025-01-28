VENV = .venv
PYTHON = $(VENV)/bin/python
UV = $(VENV)/bin/uv

.PHONY: venv test clean

venv:
	@echo "Creating virtual environment..."
	rm -rf $(VENV)
	python3 -m venv $(VENV)
	@echo "Installing base tooling..."
	$(PYTHON) -m pip install -q --disable-pip-version-check --no-cache-dir uv
	@echo "Installing project dependencies..."
	$(UV) pip install -e .[dev]

test: venv
	$(PYTHON) -m pytest -v --cov=src --cov-report=term-missing tests/

clean:
	rm -rf $(VENV) .coverage .pytest_cache build dist *.egg-info