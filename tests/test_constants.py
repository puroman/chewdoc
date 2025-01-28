import pytest
from chewdoc.constants import *

def test_template_version():
    assert TEMPLATE_VERSION == "1.2"

def test_default_exclusions():
    assert ".venv" in DEFAULT_EXCLUSIONS
    assert "dist" in DEFAULT_EXCLUSIONS

def test_error_templates():
    assert "missing_docstring" in ERROR_TEMPLATES
    assert "{item_type}" in ERROR_TEMPLATES["missing_docstring"]

def test_type_aliases():
    assert TYPE_ALIASES["List"] == "list"
    assert "Optional" in TYPE_ALIASES 