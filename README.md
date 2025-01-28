# ChewDoc

## Overview

ChewDoc is a powerful Python documentation generation tool that converts package metadata and docstrings into MyST-compatible markdown.

## Installation

```bash
python3 -m pip install git+https://github.com/puroman/chewdoc.git
```

## Quick Start

```python
from chewdoc import analyze_package, generate_docs

# Analyze a local package
result = analyze_package('./my_package', is_local=True)

# Generate documentation
generate_docs(result, output_format='myst')
```

## Features

- Extract docstrings and type information
- Generate MyST markdown documentation
- Support for local and PyPI packages
- **Smart Configuration** via `pyproject.toml`
- Customizable documentation templates
- Configurable type aliases and exclusion patterns
- Cross-reference generation toggle
- Multi-format output support (MyST, Markdown)
- Usage example size control

## Configuration
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

### Configuration Options
| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `exclude_patterns` | List[str] | `["__pycache__", "*.tests", "test_*"]` | File patterns to exclude from processing |
| `known_types` | Dict[str, str] | Common type shortcuts | Simplify complex type annotations |
| `output_format` | str | `"myst"` | Documentation format (myst/markdown) |
| `template_dir` | Path | `None` | Custom template directory |
| `enable_cross_references` | bool | `True` | Generate cross-module links |
| `max_example_lines` | int | `10` | Max lines in usage examples |

## Usage
```python
from chewdoc import analyze_package, generate_docs
from chewdoc.config import load_config

# Load configuration
config = load_config()

# Analyze package with config
package_info = analyze_package("mypackage", config=config)

# Generate docs using configuration
generate_docs(package_info, "docs/output", config=config)
```

## CLI Integration
```bash
chewdoc generate mypackage --config pyproject.toml
```

## Legacy Support
Existing code using `EXCLUDE_PATTERNS` and `KNOWN_TYPES` from constants will 
still work, but configuration file values take precedence.

## Contributing

Contributions are welcome! Please submit pull requests or open issues on our GitHub repository.

## License

MIT License 