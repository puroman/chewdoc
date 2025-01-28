VENV = .venv
PYTHON = $(VENV)/bin/python
UV = $(VENV)/bin/uv

.PHONY: venv test clean clear docs lint format

venv venv-reset:
	@echo "Creating virtual environment..."
	rm -rf $(VENV)
	python3 -m venv $(VENV)
	@echo "Installing base tooling..."
	$(PYTHON) -m pip install -q --disable-pip-version-check --no-cache-dir uv
	@echo "Installing project dependencies..."
	$(UV) pip install -e .[dev]

test: venv
	$(PYTHON) -m pytest -v --cov=src --cov-report=term-missing tests/

doc docs: venv
	@echo "Generating project documentation..."
	mkdir -p docs
	time $(PYTHON) -m chewdoc chew . --local --output docs/ --verbose

clean clear:
	rm -rf $(VENV) .coverage .pytest_cache build dist *.egg-info docs $(shell find . -name '__pycache__' -type d)

lint: venv
	$(PYTHON) -m flake8 src tests

format: venv
	$(PYTHON) -m black src tests