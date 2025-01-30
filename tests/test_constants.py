import pytest
from chewed.constants import (
    TEMPLATE_VERSION,
    DEFAULT_EXCLUSIONS,
    ERROR_TEMPLATES,
    TYPE_ALIASES,
)


def test_template_version():
    assert TEMPLATE_VERSION == "1.2"


def test_default_exclusions():
    exclusions = DEFAULT_EXCLUSIONS
    assert any(pattern in exclusions for pattern in [".venv*", "dist"])


def test_error_templates():
    assert "missing_docstring" in ERROR_TEMPLATES
    assert "{item_type}" in ERROR_TEMPLATES["missing_docstring"]


def test_type_aliases():
    assert TYPE_ALIASES["List"] == "list"
    assert "Optional" in TYPE_ALIASES
