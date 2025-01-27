CLI_HELP = {
    "package": "Generate documentation from a Python package",
    "version": "Specify package version (PyPI only)",
    "output": "Output path for generated documentation",
    "local": "Treat source as local directory"
}

META_TEMPLATE = """\
:::{{package_info}}
name: {name}
version: {version}
author: {author}
license: {license}
dependencies: {dependencies}
python_requires: {python_requires}
:::
"""

MODULE_TEMPLATE = """\
:::{{module}} {name}
{description}
{dependencies}
:::
"""

API_REF_TEMPLATE = """\
:::{{apiref}} {name}
{signature}
{doc}
:::
"""

RELATIONSHIP_TEMPLATE = """\
:::{{relationships}}
## Module Dependencies
{dependencies}

## External Dependencies
{external}
:::
""" 