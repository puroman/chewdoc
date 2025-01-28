CLI_HELP = {
    "package": "Generate documentation from a Python package",
    "version": "Specify package version (PyPI only)",
    "output": "Output path for generated documentation",
    "local": "Treat source as local directory"
}

META_TEMPLATE = """### Package Overview
**Name**: {name}  
**Version**: {version}  
**Author**: {author}  
**Interface**: {python_requires}
"""

MODULE_TEMPLATE = """\
:::{{module}} {name}
**Path**: `{path}`  
**Package**: `{package}`

{description}

{{table}}
| Attribute       | Value                          |
|-----------------|--------------------------------|
| Source Language | Python                         |
| Test Coverage   | {coverage}                     |
| Last Updated    | {last_updated}                 |
:::
"""

API_REF_TEMPLATE = """\
:::{{api-item}} {name}
**Type**: {item_type}  
**Signature**: `{signature}`  
**Defined At**: Line {line}

{doc}

{{links}}
**Related**: {links}
:::
"""

RELATIONSHIP_TEMPLATE = """\
:::{{relationships}}
## Module Relationships
{internal_deps}
:::
"""

KNOWN_TYPES = {"List", "Dict", "Optional", "Union", "Sequence", "Iterable", "Any"}

# Update exclusion patterns to match .gitignore
EXCLUDE_PATTERNS = [
    # Directories
    '.venv', '.env', '__pycache__', '.pytest_cache', 'dist', 'build',
    '*.egg-info', '.ipynb_checkpoints', '.vscode', '.idea', 'htmlcov',
    # Files
    '*.swp', '*.swo', '*.pyc', '*.pyo', '*.pyd', '*.log', '.DS_Store',
    'Thumbs.db', '.git_archival.txt', '.gitattributes'
]

# Add exclusion patterns
EXCLUDE_DIRS = ['.venv', '__pycache__']
EXCLUDE_FILES = ['__init__.py'] 