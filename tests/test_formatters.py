import pytest
from pathlib import Path
from unittest.mock import Mock
from src.chewdoc.formatters.myst_writer import MystWriter
from src.chewdoc.config import ChewdocConfig

@pytest.fixture
def base_package():
    return {
        "name": "testpkg",
        "package": "testpkg",
        "version": "1.0.0",
        "author": "Test Author",
        "license": "MIT",
        "dependencies": ["requests"],
        "python_requires": ">=3.8",
        "config": ChewdocConfig(),
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
            },
            "constants": {},
            "layer": "application",
            "role": "API interface",
            "path": "/path/testmod.py"
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
        "package": "minimalpkg",
        "version": "0.0.0",
        "author": "Unknown Author",
        "license": "Proprietary",
        "modules": [{"name": "testmod", "internal_deps": []}],
        "python_requires": ">=3.6"
    }
    
    output = tmp_path / "output.myst"
    writer.generate(minimal_data, output)
    
    content = output.read_text()
    assert "**Version**: 0.0.0" in content
    assert "**Author**: Unknown Author" in content

def test_module_relationships_in_output(tmp_path, base_package):
    output_path = tmp_path / "output.md"
    writer = MystWriter(ChewdocConfig())
    writer.generate(base_package, output_path)
    content = output_path.read_text()
    assert "## testmod" in content
    assert "**Imports**: os, sys" in content
    assert "Functions: " not in content


def test_module_relationship_visualization(tmp_path):
    test_data = {
        "name": "testpkg",
        "version": "1.0",
        "author": "Tester",
        "license": "MIT",
        "package": "testpkg",
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
    writer = MystWriter(ChewdocConfig())
    writer.generate(test_data, output)

    content = output.read_text()
    assert "[[other.module]]" in content
    assert "`os`" in content


def test_format_empty_module(tmp_path):
    test_data = create_test_package(
        modules=[create_test_module("emptymod")]
    )
    
    output = tmp_path / "output.myst"
    writer = MystWriter(ChewdocConfig())
    writer.generate(test_data, output)
    
    content = output.read_text()
    assert "emptymod" in content


def test_known_type_formatting(tmp_path):
    test_data = create_test_package(
        modules=[create_test_module(
            "testmod",
            type_info={
                "cross_references": {"List"},
                "functions": {
                    "test": {
                        "args": {"items": "List[int]"},
                        "returns": "Optional[str]"
                    }
                }
            }
        )]
    )
    
    output = tmp_path / "output.myst"
    writer = MystWriter(ChewdocConfig())
    writer.generate(test_data, output)
    
    content = output.read_text()
    assert "[List[int]](#list)" in content


def test_myst_empty_input(tmp_path):
    with pytest.raises(ValueError):
        writer = MystWriter(ChewdocConfig())
        writer.generate({}, tmp_path / "output.myst")


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
    writer = MystWriter(ChewdocConfig())
    writer.generate(test_data, output)
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
    writer = MystWriter(ChewdocConfig())
    writer.generate(test_data, output)

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
    writer = MystWriter(ChewdocConfig())
    writer.generate(test_data, output)

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
    writer = MystWriter(ChewdocConfig())
    writer.generate(test_data, output)
    
    content = output.read_text()
    assert "## Usage Examples" in content
    assert ">>> print('example')" in content
    assert "**Test case**: `test_usage`" in content

def create_test_module(name="testmod", **kwargs):
    """Helper to create consistent test module data"""
    base = {
        "name": name,
        "path": f"/path/{name}.py",
        "internal_deps": [],
        "imports": [],
        "type_info": {
            "cross_references": set(),
            "functions": {},
            "classes": {},
            "variables": {}
        },
        "docstrings": {},
        "examples": []
    }
    return {**base, **kwargs}

def create_test_package(name="testpkg", **kwargs):
    """Helper to create consistent test package data"""
    base = {
        "name": name,
        "package": name,
        "version": "1.0.0",
        "author": "Test Author",
        "license": "MIT",
        "dependencies": [],
        "python_requires": ">=3.8",
        "modules": []
    }
    return {**base, **kwargs}
