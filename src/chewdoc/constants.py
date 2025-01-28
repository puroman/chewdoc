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
**Dependencies**: {dependencies}
"""

MODULE_TEMPLATE = """\
:::{{module}} {name}
{description}
{dependencies}
:::
"""

API_REF_TEMPLATE = """`{name}`{signature}
{doc}
"""

RELATIONSHIP_TEMPLATE = """\
:::{{relationships}}
## Module Dependencies
{dependencies}

## External Dependencies
{external}
:::
"""

KNOWN_TYPES = {"List", "Dict", "Optional", "Union", "Sequence", "Iterable", "Any"} 