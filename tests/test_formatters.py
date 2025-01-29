from src.chewdoc.formatters.myst_writer import MystWriter
from pathlib import Path
import ast
import pytest


def test_myst_writer_basic(tmp_path):
    writer = MystWriter()
    package_info = {
        "package": "testpkg",
        "modules": [{"name": "testmod", "docstrings": {"module": "Test module"}}],
        "config": {},
    }

    writer.generate(package_info, tmp_path)
    assert (tmp_path / "index.md").exists()
    assert "## Modules" in (tmp_path / "index.md").read_text()


def test_myst_writer_simple_module(tmp_path):
    writer = MystWriter()
    package_info = {
        "package": "testpkg",
        "modules": [
            {
                "name": "testmod",
                "docstrings": {"module": "Test docs"},
                "examples": [{"type": "doctest", "content": ">>> 1+1"}],
            }
        ],
    }
    writer.generate(package_info, tmp_path)
    assert (tmp_path / "testmod.md").exists()


def test_myst_writer_complex_module(tmp_path):
    writer = MystWriter()
    package_info = {
        "package": "testpkg",
        "modules": [
            {
                "name": "testmod",
                "docstrings": {
                    "module": "Module doc",
                    "class": "TestClass",
                    "function": "test_func",
                },
                "examples": [{"type": "doctest", "content": ">>> 1+1"}],
                "type_info": {
                    "classes": {
                        "TestClass": {
                            "methods": {
                                "__init__": {"args": {"args": [], "defaults": []}}
                            },
                            "doc": "Class docstring",
                        },
                        "EmptyClass": {},
                    },
                    "functions": {
                        "test_func": {
                            "args": ast.arguments(args=[ast.arg(arg="param")]),
                            "returns": ast.Constant(value=str),
                        }
                    },
                    "cross_references": ["othermod"],
                },
            }
        ],
    }
    writer.generate(package_info, tmp_path)
    content = (tmp_path / "testmod.md").read_text()

    assert "## TestClass" in content
    assert "Class docstring" in content
    assert "### Methods" in content
    assert "## `test_func(param) -> str`" in content
    assert "[[TestClass]]" in content


def test_myst_writer_minimal_module(tmp_path):
    """Test module with minimal content"""
    writer = MystWriter()
    package_info = {
        "package": "testpkg",
        "modules": [
            {
                "name": "bare_module",
                "docstrings": {},
                "type_info": {
                    "variables": {"MAX_LIMIT": {"value": 100}},
                    "cross_references": [],
                },
            }
        ],
    }
    writer.generate(package_info, tmp_path)
    content = (tmp_path / "bare_module.md").read_text()
    assert "## API Reference" not in content
    assert "MAX_LIMIT" in content


def test_myst_writer_error_handling(tmp_path):
    """Test malformed AST data handling"""
    writer = MystWriter()
    package_info = {
        "package": "testpkg",
        "modules": [
            {
                "name": "broken_mod",
                "type_info": {"functions": {"bad_func": {"args": "not-an-ast-node"}}},
            }
        ],
    }

    with pytest.raises(ValueError) as excinfo:
        writer.generate(package_info, tmp_path)
    assert "Malformed arguments node" in str(excinfo.value)


def test_myst_writer_invalid_examples(tmp_path, caplog):
    """Test handling of malformed examples in MystWriter."""
    writer = MystWriter()
    package_info = {
        "package": "testpkg",
        "modules": [
            {
                "name": "bad_examples",
                "examples": [
                    "print('valid string')",
                    {"content": "another valid"},
                    ["invalid list example"],
                    42,
                    {"type": "pytest"},  # Missing code
                ],
            }
        ],
    }

    writer.generate(package_info, tmp_path)
    assert "Skipping invalid example" in caplog.text
    assert "Expected dict" in caplog.text
    assert "Missing code/content" in caplog.text
