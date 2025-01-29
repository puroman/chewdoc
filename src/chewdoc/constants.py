"""
Centralized constants for chewdoc documentation generator

Organized into sections:
- Template Configuration
- AST Processing
- Error Handling
- Default Configuration
"""

# Template Configuration
import ast


TEMPLATE_VERSION = "1.2"
META_TEMPLATE = """### Package Overview
**Name**: {name}
**Version**: {version}
**Author**: {author}
**License**: {license}
**Interface**: {python_requires}
"""

MODULE_TEMPLATE = """# {name}

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

# AST Processing
AST_NODE_TYPES = {
    "MODULE": ast.Module,
    "CLASS": ast.ClassDef,
    "FUNCTION": ast.FunctionDef,
}

# Error Handling
ERROR_TEMPLATES = {
    "missing_docstring": "No documentation found for {item_type} {item_name}",
    "invalid_crossref": "Broken link to {target} in {source}",
    "template_error": "Invalid template version {found} (expected {expected})",
}

# Default Configuration
DEFAULT_EXCLUSIONS = [
    "__pycache__",
    ".*",
    "tests/*",
    "docs/*",
    "build/*",
    "dist/*",
    "venv*",
    ".venv*",
    "env*"
]

TYPE_ALIASES = {"List": "list", "Dict": "dict", "Optional": "typing.Optional"}

# CLI Configuration
CLI_HELP = {
    "package": "Generate documentation from a Python package",
    "version": "Specify package version (PyPI only)",
    "output": "Output path for generated documentation",
    "local": "Treat source as local directory",
    "context": "Documentation detail level (basic|full|ai-assisted)",
}
