from src.chewdoc.formatters.myst_writer import MystWriter
from pathlib import Path
import ast

def test_myst_writer_basic(tmp_path):
    writer = MystWriter()
    package_info = {
        "package": "testpkg",
        "modules": [{
            "name": "testmod",
            "docstrings": {"module": "Test module"}
        }],
        "config": {}
    }
    
    writer.generate(package_info, tmp_path)
    assert (tmp_path / "index.md").exists()
    assert "## Modules" in (tmp_path / "index.md").read_text()

def test_myst_writer_simple_module(tmp_path):
    writer = MystWriter()
    package_info = {
        "package": "testpkg",
        "modules": [{
            "name": "testmod",
            "docstrings": {"module": "Test docs"},
            "examples": [{"type": "doctest", "content": ">>> 1+1"}]
        }]
    }
    writer.generate(package_info, tmp_path)
    assert (tmp_path / "testmod.md").exists()

def test_myst_writer_complex_module(tmp_path):
    writer = MystWriter()
    package_info = {
        "package": "testpkg",
        "modules": [{
            "name": "testmod",
            "docstrings": {"module": "Module doc", "class": "TestClass", "function": "test_func"},
            "examples": [{"type": "doctest", "content": ">>> 1+1"}],
            "type_info": {
                "classes": {
                    "TestClass": {
                        "methods": {"__init__": {"args": {"args": [], "defaults": []}}},
                        "doc": "Class docstring"
                    },
                    "EmptyClass": {}
                },
                "functions": {
                    "test_func": {
                        "args": ast.arguments(args=[ast.arg(arg="param")]),
                        "returns": ast.Constant(value=str)
                    }
                },
                "cross_references": ["othermod"]
            }
        }]
    }
    writer.generate(package_info, tmp_path)
    content = (tmp_path / "testmod.md").read_text()
    
    assert "## TestClass" in content
    assert "Class docstring" in content
    assert "### Methods" in content
    assert "## `test_func(param) -> str`" in content
    assert "[[TestClass]]" in content