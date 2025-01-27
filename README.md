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

## Contributing

Contributions are welcome! Please submit pull requests or open issues on our GitHub repository.

## License

MIT License 