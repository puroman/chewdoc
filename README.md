# ChewDoc

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Code documentation toolkit** for analyzing and generating LLM-friendly, but human-readable and lovable code documentation.

## Features

- Code structure analysis using Python's AST
- Configurable documentation generation (MyST/Markdown)
- Automatic type annotation resolution
- Cross-component relationship mapping
- Example extraction from docstrings and tests
- Flexible configuration via `pyproject.toml`

## Roadmap

- [ ] LLM-assisted documentation analysis & generation

## Installation

```bash
# Install with pip substitute
python3 -m pip install uv
uv pip install git+https://github.com/puroman/chewdoc.git

# Editable install for contributors
git clone https://github.com/puroman/chewdoc.git
cd chewdoc && uv pip install -e .
```

## Get Started

```bash
# Generate docs for current project (default output dir)
chew . --output docs/

# Analyze specific package
chew ./my_module --output docs/ --verbose
chew requests --output docs/requests --local
```

### Research Notes
```python
from chewdoc import analyze_package, generate_docs

# Experimental analysis pipeline
results = analyze_package("mypackage")
generate_docs(results, output_format="myst")
```

> **Note:** ChewDoc is a research prototype - interfaces may evolve as we explore new documentation paradigms.

## Configuration

Add to `pyproject.toml`:
```toml
[tool.chewdoc]
output_format = "myst"
exclude_patterns = ["tests/*"]
known_types = { "DataFrame" = "pandas.DataFrame" }
```

| Setting | Description |
|---------|-------------|
| `output_format` | Documentation format (myst/markdown) |
| `exclude_patterns` | File patterns to ignore |
| `known_types` | Type annotation simplifications |

## Project Structure

```
chewdoc/
├── src/
│   └── chewdoc/       # Core research implementation
│       ├── analysis/  # AST processing components
│       └── formats/   # Output format handlers
├── tests/             # Experimental validation
└── pyproject.toml
```

## Contributing

We welcome collaborations expecialy from research teams! 
We would like to work on the following topics:
- Benchmarking methodologies
- Documentation patterns research
- Experimental design principles
- LLM-assisted and LLM-led documentation workflows
- Natural language documentation generation
- On-demand documentation generation
- Usage examples generation

Please see our [contribution guidelines](CONTRIBUTING.md) for more details.

---

_MIT Licensed | Part of ongoing research into API documentation systems and agentic workflow automation_

