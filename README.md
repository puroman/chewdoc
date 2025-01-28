# ChewDoc :notebook_with_decorative_cover:

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Intelligent documentation generator that creates LLM-optimized documentation with rich type information and usage examples.

## Features :sparkles:

- **AST-based Analysis**: Deep code structure analysis using Python's Abstract Syntax Trees
- **Multi-format Output**: Generate MyST markdown or basic Markdown documentation
- **Smart Type Inference**: Automatic type annotation resolution with configurable aliases
- **Cross-references**: Automatic links between related components
- **Usage Examples**: Extract and format examples from docstrings and test cases
- **Configurable**: Control through `pyproject.toml` or programmatic API
- **Dependency Mapping**: Visualize module relationships with Mermaid diagrams

## Installation :package:

```bash
# Install with UV (recommended)
python3 -m pip install uv
uv pip install git+https://github.com/puroman/chewdoc.git

# For development (editable install)
git clone https://github.com/puroman/chewdoc.git
cd chewdoc
uv pip install -e .
```

## Quick Start :rocket:

### CLI Usage
```bash
# Generate docs for local package
chewdoc generate ./my_package --local --output docs/

# Generate docs for PyPI package
chewdoc generate requests --output docs/
```

### Programmatic API
```python
from chewdoc import analyze_package, generate_docs
from chewdoc.config import load_config

config = load_config()  # Load from pyproject.toml
package_info = analyze_package("mypackage", config=config)
generate_docs(
    package_info,
    output_format="myst",
    output_path="docs/",
    enable_cross_refs=True
)
```

## Configuration :wrench:

Add a `[tool.chewdoc]` section to your `pyproject.toml`:

```toml
[tool.chewdoc]
exclude_patterns = ["__pycache__", "*.test"]
known_types = { "Sequence" = "collections.abc.Sequence" }
output_format = "myst"
template_dir = "docs/templates"
enable_cross_references = true
max_example_lines = 15
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `exclude_patterns` | List[str] | [".venv*", "__pycache__", ...] | File patterns to exclude |
| `known_types` | Dict[str, str] | Common type shortcuts | Simplify complex type annotations |
| `output_format` | str | "myst" | Documentation format (myst/markdown) |
| `template_dir` | Path | None | Custom template directory |
| `enable_cross_references` | bool | True | Generate cross-module links |
| `max_example_lines` | int | 10 | Max lines in usage examples |

## Project Structure :file_folder:

```
chewdoc/
├── src/
│   ├── chewdoc/
│   │   ├── core.py        # Main analysis logic
│   │   ├── formatters/    # Output generators (MyST/Markdown)
│   │   ├── utils.py       # Shared utilities
│   │   ├── config.py      # Configuration handling
│   │   └── cli.py         # Command line interface
├── tests/                 # Unit and integration tests
├── pyproject.toml         # Build configuration
└── README.md              # This documentation
```

## Advanced Usage :microscope:

### Custom Templates
Create custom templates in a `templates/` directory:
```python
# docs/templates/module.md.j2
# {{ module.name }}

{{ module.description }}

{% if module.examples %}
## Usage Examples
{% for example in module.examples %}
```python
{{ example.code }}
```
{% endfor %}
{% endif %}
```

### Type Annotation Handling
Configure complex types in `pyproject.toml`:
```toml
[tool.chewdoc.known_types]
"numpy.ndarray" = "NDArray"
"pandas.DataFrame" = "DataFrame"
```

## Running Tests :test_tube:

```bash
uv pip install -r requirements-test.txt
pytest tests/ --cov=chewdoc -v

# With coverage report
pytest tests/ --cov=chewdoc --cov-report=html
```

## Contributing :handshake:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes with semantic messages
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please follow existing code style and add tests for new features.

## License :scroll:

MIT License - See [LICENSE](LICENSE) for details 