CLI_HELP = {
    "package": "Generate documentation from a Python package",
    "version": "Specify package version (PyPI only)",
    "output": "Output path for generated documentation",
    "local": "Treat source as local directory",
    "context": "Documentation detail level (basic|full|ai-assisted)"
}

META_TEMPLATE = """### Package Overview
**Name**: {name}
**Version**: {version}
**Author**: {author}
**Interface**: {python_requires}
"""

MODULE_TEMPLATE = """\
:::{{module}} {name}

### Module Context
- **Package**: `{package}`
{role_section}
{layer_section}

### Responsibilities
{description}

### Component Graph
```mermaid
graph TD
    {dependencies}
```

### Usage Examples
```python
{usage_examples}
```
:::
"""

API_REF_TEMPLATE = """\
:::{{api-item}} {name}

### Component Overview
- **Type**: {item_type}
- **Purpose**: {purpose}
- **Interface**: `{signature}`

### Documentation
{doc}

### Related Components
```mermaid
graph LR
    {name} --> {links}
```
:::
"""

RELATIONSHIP_TEMPLATE = """\
:::{{relationships}}

### Module Dependencies
```mermaid
graph TD
    {internal_deps}
```

### Key Interactions
{interaction_patterns}
:::
"""

# Expanded type definitions for better context
KNOWN_TYPES = {
    # Core types
    "List", "Dict", "Optional", "Union", "Sequence", "Iterable", "Any",
    # Context managers
    "ContextManager", "AsyncContextManager",
    # Async types
    "Coroutine", "AsyncIterator", "AsyncGenerator",
    # Callable types
    "Callable", "Generator", "TypeVar"
}

# Consolidated exclusion patterns
EXCLUDE_PATTERNS = [
    # Development artifacts
    '.venv', '.env', '__pycache__', '.pytest_cache', 'dist', 'build',
    '*.egg-info', '.ipynb_checkpoints', '.git*',
    # IDE files
    '.vscode', '.idea',
    # System files
    '*.pyc', '*.pyo', '*.pyd', '*.log', '.DS_Store', 'Thumbs.db'
]

# Simplified exclusion patterns
EXCLUDE_DIRS = ['.venv', '__pycache__', '.git', 'dist', 'build']
EXCLUDE_FILES = ['__init__.py', '*.pyc', '*.pyo'] 