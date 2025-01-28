import pytest
from pathlib import Path
from unittest.mock import Mock
from src.chewdoc.formatters.myst_writer import MystWriter
from src.chewdoc.config import ChewdocConfig

@pytest.fixture
def base_package():
    return {
        "name": "testpkg",
        "version": "1.0.0",
        "author": "Test Author",
        "license": "MIT",
        "dependencies": ["requests"],
        "python_requires": ">=3.8",
        "package": "testpkg",
        "internal_deps": [],
        "modules": [{
            "name": "testmod",
            "docstrings": {"module:1": "Module docstring"},
            "examples": [],
            "imports": [],
            "internal_deps": [],
            "type_info": {
                "cross_references": set(),
                "functions": {},
                "classes": {},
                "variables": {}
            }
        }]
    }

@pytest.fixture
def config():
    return ChewdocConfig()

def test_myst_basic_generation(tmp_path, base_package):
    writer = MystWriter(ChewdocConfig())
    output_path = tmp_path / "output.md"
    
    writer.generate(base_package, output_path)
    
    content = output_path.read_text()
    assert "# testpkg Documentation" in content
    assert "## testmod" in content
    assert "Module docstring" in content

def test_myst_example_generation(tmp_path, base_package):
    base_package["modules"][0]["examples"] = [{
        "type": "doctest",
        "content": ">>> print('test')\n'test'"
    }]
    
    writer = MystWriter(ChewdocConfig())
    output_path = tmp_path / "output.md"
    writer.generate(base_package, output_path)
    
    content = output_path.read_text()
    assert "### Usage Examples" in content
    assert ">>> print('test')" in content

def test_myst_type_references(tmp_path, base_package):
    base_package["modules"][0]["type_info"]["cross_references"] = {"MyType"}
    base_package["modules"][0]["type_info"]["functions"] = {
        "test": {"args": {"param": "MyType"}, "returns": "Optional[MyType]"}
    }
    
    writer = MystWriter(ChewdocConfig())
    output_path = tmp_path / "output.md"
    writer.generate(base_package, output_path)
    
    content = output_path.read_text()
    assert "[[MyType]]" in content
    assert "Optional[[MyType]]" in content

def test_module_with_examples(tmp_path, base_package, config):
    writer = MystWriter(config)
    test_module = {
        "name": "testmod",
        "examples": [
            {
                "type": "doctest",
                "content": ">>> print('example')\n'example'",
                "line": 5
            }
        ]
    }
    base_package["modules"].append(test_module)
    
    output = tmp_path / "output.myst"
    writer.generate(base_package, output)
    
    content = output.read_text()
    assert "Usage Examples" in content
    assert ">>> print('example')" in content

def test_cross_reference_formatting(tmp_path, base_package, config):
    writer = MystWriter(config)
    test_module = {
        "name": "testmod",
        "type_info": {
            "cross_references": ["MyType", "external.Type"],
            "functions": {
                "test": {
                    "args": {"arg": "MyType"},
                    "returns": "List[external.Type]",
                }
            }
        }
    }
    base_package["modules"].append(test_module)
    
    output = tmp_path / "output.myst"
    writer.generate(base_package, output)
    
    content = output.read_text()
    assert "[[MyType]]" in content
    assert "[[external.Type]]" in content

def test_metadata_fallbacks(tmp_path, config):
    writer = MystWriter(config)
    minimal_data = {
        "name": "minimalpkg",
        "version": "0.0.0",
        "author": "Unknown Author",
        "modules": [{"name": "testmod"}]
    }
    
    output = tmp_path / "output.myst"
    writer.generate(minimal_data, output)
    
    content = output.read_text()
    assert "**Version**: 0.0.0" in content
    assert "**Author**: Unknown Author" in content

def test_module_relationships_in_output(tmp_path, base_package):
    writer = MystWriter(ChewdocConfig())
    writer.generate(base_package, tmp_path / "output.md")

    content = (tmp_path / "output.md").read_text()
    assert "## testmod" in content
    assert "**Imports**: os, sys" in content
    assert "Functions: " not in content


def test_module_relationship_visualization(tmp_path):
    test_data = {
        "name": "testpkg",
        "version": "1.0",
        "author": "Tester",
        "modules": [
            {
                "name": "testmod",
                "imports": ["os", "other.module"],
                "internal_deps": ["other.module"],
                "path": "/path/testmod.py",
                "type_info": {
                    "cross_references": set(),
                    "functions": {},
                    "classes": {},
                    "variables": {},
                },
            }
        ],
    }

    output = tmp_path / "output.myst"
    generate_myst(test_data, output)

    content = output.read_text()
    assert "[[other.module]]" in content
    assert "`os`" in content


def test_format_empty_module(tmp_path):
    test_data = {
        "name": "testpkg",
        "modules": [
            {
                "name": "emptymod",
                "imports": [],
                "internal_deps": [],
                "path": "/path/emptymod.py",
                "type_info": {
                    "cross_references": set(),
                    "functions": {},
                    "classes": {},
                    "variables": {},
                },
                "docstrings": {},
            }
        ],
    }

    output = tmp_path / "output.myst"
    generate_myst(test_data, output)

    content = output.read_text()
    assert "emptymod" in content
    assert "No type references" not in content


def test_known_type_formatting(tmp_path):
    test_data = {
        "name": "testpkg",
        "version": "1.0",
        "author": "Tester",
        "license": "MIT",
        "dependencies": [],
        "python_requires": ">=3.8",
        "modules": [
            {
                "name": "testmod",
                "path": "/path/testmod.py",
                "imports": [],
                "internal_deps": [],
                "type_info": {
                    "cross_references": {"List"},
                    "functions": {
                        "test": {
                            "args": {"items": "List[int]"},
                            "returns": "Optional[str]",
                        }
                    },
                    "classes": {},
                    "variables": {},
                },
                "docstrings": {},
            }
        ],
    }

    output = tmp_path / "output.myst"
    generate_myst(test_data, output)

    content = output.read_text()
    assert "[List[int]](#list)" in content
    assert "[Optional[str]](#optional)" in content


def test_myst_empty_input():
    with pytest.raises(ValueError):
        generate_myst({}, Path("/invalid"))


def test_class_formatting(tmp_path):
    test_data = {
        "name": "testpkg",
        "version": "1.0",
        "author": "Tester",
        "modules": [
            {
                "name": "testmod",
                "type_info": {
                    "classes": {
                        "TestClass": {"attributes": {"name": "str", "value": "int"}}
                    }
                },
            }
        ],
    }

    output = tmp_path / "output.myst"
    generate_myst(test_data, output)
    content = output.read_text()
    assert "**TestClass**" in content
    assert "name: str" in content
    assert "value: int" in content


def test_empty_type_info(tmp_path):
    test_data = {
        "modules": [
            {
                "name": "testmod",
                "type_info": {
                    "cross_references": set(),
                    "functions": {},
                    "classes": {},
                    "variables": {},
                },
            }
        ]
    }

    output = tmp_path / "output.myst"
    generate_myst(test_data, output)

    content = output.read_text()
    assert "Type References" not in content
    assert "Functions" not in content
    assert "Classes" not in content


def test_generic_type_formatting(tmp_path):
    test_data = {
        "modules": [
            {
                "name": "testmod",
                "type_info": {
                    "functions": {
                        "test": {
                            "args": {"items": "List[Dict[str, int]]"},
                            "returns": "Optional[float]",
                        }
                    }
                },
            }
        ]
    }

    output = tmp_path / "output.myst"
    generate_myst(test_data, output)

    content = output.read_text()
    assert "[List[Dict[str, int]]](#list)" in content
    assert "[Optional[float]](#optional)" in content


def test_example_formatting(tmp_path):
    test_data = {
        "modules": [{
            "name": "testmod",
            "examples": [
                {
                    "type": "doctest", 
                    "content": ">>> print('example')\n'example'",
                    "line": 5
                },
                {
                    "type": "pytest",
                    "name": "test_usage",
                    "content": "def test_usage():\n    assert True",
                    "line": 10
                }
            ]
        }]
    }

    output = tmp_path / "output.myst"
    generate_myst(test_data, output)
    
    content = output.read_text()
    assert "## Usage Examples" in content
    assert ">>> print('example')" in content
    assert "**Test case**: `test_usage`" in content
