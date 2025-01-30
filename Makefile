VENV = .venv
PYTHON = $(VENV)/bin/python
UV = uv
DOCS_DIR = docs

# Test configuration parameters with default values
# TEST_PATH: Directory containing test files (default: tests/)
TEST_PATH ?= tests/
# TEST_MARKERS: Pytest markers to filter specific test groups (default: none)
TEST_MARKERS ?= 
# TEST_VERBOSITY: Controls test output verbosity (-v, -vv, or empty for quiet)
TEST_VERBOSITY ?= -v
# TEST_WORKERS: Number of parallel workers for test execution (auto or specific number)
TEST_WORKERS ?= auto
# COVERAGE_FORMAT: Format for coverage reporting (term-missing, html, xml)
COVERAGE_FORMAT ?= term-missing
# COVERAGE_MIN: Minimum required test coverage percentage (default: 80%)
COVERAGE_MIN ?= 80

# Helper function to handle test markers
MARKER_OPTION = $(if $(TEST_MARKERS),-m "$(TEST_MARKERS)",)

.PHONY: venv test test-cov test-html test-xml test-parallel test-watch clean clear docs lint format help

help:
	@echo "Available commands:"
	@echo "  make install       - Install all dependencies (prod + dev)"
	@echo "  make install-prod  - Install production dependencies only"
	@echo "  make install-dev   - Install development dependencies only"
	@echo "  make test          - Run tests"
	@echo "  make test-cov      - Run tests with coverage report"
	@echo "  make test-html     - Run tests with HTML coverage report"
	@echo "  make test-xml      - Run tests with XML coverage report"
	@echo "  make test-parallel - Run tests in parallel"
	@echo "  make test-watch    - Run tests in watch mode"
	@echo "  make docs          - Generate documentation"
	@echo "  make lint          - Run linting checks"
	@echo "  make format        - Format code"
	@echo "  make clean         - Clean build artifacts"
	@echo ""
	@echo "Parameters:"
	@echo "  TEST_PATH         - Path to test files (default: tests/)"
	@echo "  TEST_MARKERS      - Pytest markers to filter tests (empty by default)"
	@echo "  TEST_VERBOSITY    - Test output verbosity (-v, -vv, or '')"
	@echo "  TEST_WORKERS      - Number of parallel workers (auto, or number)"
	@echo "  COVERAGE_FORMAT   - Coverage report format (term-missing, html, xml)"
	@echo "  COVERAGE_MIN      - Minimum coverage percentage (default: 80)"

venv:
	@echo "Checking system requirements..."
	@command -v $(UV) >/dev/null 2>&1 || { echo >&2 "Error: uv not found. Please install uv first (https://github.com/astral-sh/uv)."; exit 1; }
	@echo "Creating virtual environment..."
	rm -rf $(VENV)
	$(UV) venv $(VENV)
	@echo "Installing base dependencies..."
	$(UV) pip install --python $(VENV)/bin/python -e .[dev]

# Installation targets
install: venv install-prod install-dev

install-prod: venv
	@echo "Installing production dependencies..."
	$(UV) pip install -e .

install-dev: venv
	@echo "Installing development dependencies..."
	$(UV) pip install --python $(VENV)/bin/python -e .[dev]

test: venv
	$(PYTHON) -m pytest $(TEST_VERBOSITY) $(MARKER_OPTION) $(TEST_PATH)

covtest-cov: venv
	$(PYTHON) -m pytest $(TEST_VERBOSITY) $(MARKER_OPTION) \
		--cov=src \
		--cov-report=$(COVERAGE_FORMAT) \
		--cov-fail-under=$(COVERAGE_MIN) \
		$(TEST_PATH)

test-html: COVERAGE_FORMAT=html
test-html: test-cov
	@echo "Coverage report generated in htmlcov/index.html"

test-xml: COVERAGE_FORMAT=xml
test-xml: test-cov
	@echo "Coverage report generated in coverage.xml"

test-parallel: venv
	$(PYTHON) -m pytest $(TEST_VERBOSITY) $(MARKER_OPTION) \
		-n $(TEST_WORKERS) \
		$(TEST_PATH)

test-watch: venv
	$(PYTHON) -m pytest-watch -- $(TEST_VERBOSITY) $(MARKER_OPTION) $(TEST_PATH)

doc docs: install-dev
	@echo "📚 Generating project documentation..."
	@mkdir -p $(DOCS_DIR)
	@echo "🕒 Timing documentation generation..."
	@time $(PYTHON) -m chewdoc chew src/chewdoc/ --output $(DOCS_DIR)/ --local --verbose
	@echo "✅ Documentation generated at: $(DOCS_DIR)/"

clean clear:
	rm -rf .venv* .coverage .pytest_cache build dist *.egg-info docs htmlcov coverage.xml $(shell find . -name '__pycache__' -type d)

lint: venv
	$(PYTHON) -m flake8 --max-line-length=88 --ignore=F401,E203,W503 src tests

format: venv
	$(PYTHON) -m black src tests

# Default target
.DEFAULT_GOAL := help