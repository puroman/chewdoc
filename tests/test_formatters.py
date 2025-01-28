import pytest
from pathlib import Path
from chewdoc.formatters.myst_writer import generate_myst

def test_myst_generation(tmp_path):
    test_data = {
        "name": "testpkg",
        "version": "1.0",
        "author": "Tester",
        "license": "MIT",
        "dependencies": ["requests"],
        "python_requires": ">=3.8",
        "modules": [{
            "name": "testmod",
            "path": "/path/testmod.py",
            "imports": [],
            "internal_deps": [],
            "types": {
                "cross_references": set(),
                "functions": {},
                "classes": {},
                "variables": {}
            },
            "docstrings": {
                "module:1": "Module docstring",
                "test_fn:5": "Function docstring"
            }
        }]
    }
    
    output = tmp_path / "output.myst"
    generate_myst(test_data, output)
    
    content = output.read_text()
    assert "# Package: testpkg" in content
    assert "Function docstring" in content
    assert ":::{doc} test_fn" in content 

def test_module_relationships_in_output(tmp_path):
    test_data = {
        "name": "testpkg",
        "version": "1.0",
        "author": "Tester",
        "license": "MIT",
        "dependencies": [],
        "python_requires": ">=3.8",
        "modules": [{
            "name": "testmod",
            "path": "/path/testmod.py",
            "imports": ["os", "sys"],
            "internal_deps": [],
            "types": {
                "cross_references": set(),
                "functions": {},
                "classes": {},
                "variables": {}
            },
            "docstrings": {}
        }]
    }
    
    output = tmp_path / "output.myst"
    generate_myst(test_data, output)
    
    content = output.read_text()
    assert "## testmod" in content
    assert "**Imports**: os, sys" in content
    assert "Functions: " not in content

def test_cross_reference_validation(tmp_path):
    test_data = {
        "name": "testpkg",
        "version": "1.0",
        "author": "Tester",
        "license": "MIT",
        "dependencies": [],
        "python_requires": ">=3.8",
        "modules": [{
            "name": "testmod",
            "path": "/path/testmod.py",
            "imports": [],
            "internal_deps": [],
            "types": {
                "cross_references": ["MyType", "external.Type"],
                "functions": {
                    "test": {
                        "args": {"arg": "MyType"},
                        "returns": "List[external.Type]"
                    }
                },
                "classes": {},
                "variables": {}
            }
        }]
    }
    
    output = tmp_path / "output.myst"
    generate_myst(test_data, output)
    
    content = output.read_text()
    assert "[[MyType]]" in content
    assert "[[external.Type]]" in content
    assert "[List[external.Type]]" in content 

def test_module_relationship_visualization(tmp_path):
    test_data = {
        "name": "testpkg",
        "version": "1.0",
        "author": "Tester",
        "modules": [{
            "name": "testmod",
            "imports": ["os", "other.module"],
            "internal_deps": ["other.module"],
            "path": "/path/testmod.py",
            "types": {
                "cross_references": set(),
                "functions": {},
                "classes": {},
                "variables": {}
            }
        }]
    }
    
    output = tmp_path / "output.myst"
    generate_myst(test_data, output)
    
    content = output.read_text()
    assert "[[other.module]]" in content
    assert "`os`" in content

def test_format_empty_module(tmp_path):
    test_data = {
        "name": "testpkg",
        "modules": [{
            "name": "emptymod",
            "imports": [],
            "internal_deps": [],
            "path": "/path/emptymod.py",
            "types": {
                "cross_references": set(),
                "functions": {},
                "classes": {},
                "variables": {}
            },
            "docstrings": {}
        }]
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
        "modules": [{
            "name": "testmod",
            "path": "/path/testmod.py",
            "imports": [],
            "internal_deps": [],
            "types": {
                "cross_references": {"List"},
                "functions": {
                    "test": {
                        "args": {"items": "List[int]"},
                        "returns": "Optional[str]"
                    }
                },
                "classes": {},
                "variables": {}
            },
            "docstrings": {}
        }]
    }
    
    output = tmp_path / "output.myst"
    generate_myst(test_data, output)
    
    content = output.read_text()
    assert "[List[int]](#list)" in content
    assert "[Optional[str]](#optional)" in content 

def test_myst_empty_input():
    with pytest.raises(ValueError):
        generate_myst({}, Path("/invalid"))

def test_myst_metadata_fallbacks():
    test_data = {"name": "minimal"}
    output = Path("/tmp/test.myst")
    generate_myst(test_data, output)
    content = output.read_text()
    assert "**Version**: 0.0.0" in content
    assert "**Author**: Unknown Author" in content 

def test_class_formatting(tmp_path):
    test_data = {
        "name": "testpkg",
        "version": "1.0",
        "author": "Tester",
        "modules": [{
            "name": "testmod",
            "types": {
                "classes": {
                    "TestClass": {
                        "attributes": {"name": "str", "value": "int"}
                    }
                }
            }
        }]
    }
    
    output = tmp_path / "output.myst"
    generate_myst(test_data, output)
    content = output.read_text()
    assert "**TestClass**" in content
    assert "name: str" in content
    assert "value: int" in content 

def test_empty_type_info(tmp_path):
    test_data = {
        "modules": [{
            "name": "testmod",
            "types": {
                "cross_references": set(),
                "functions": {},
                "classes": {},
                "variables": {}
            }
        }]
    }
    
    output = tmp_path / "output.myst"
    generate_myst(test_data, output)
    
    content = output.read_text()
    assert "Type References" not in content
    assert "Functions" not in content
    assert "Classes" not in content 

def test_generic_type_formatting(tmp_path):
    test_data = {
        "modules": [{
            "name": "testmod",
            "types": {
                "functions": {
                    "test": {
                        "args": {"items": "List[Dict[str, int]]"},
                        "returns": "Optional[float]"
                    }
                }
            }
        }]
    }
    
    output = tmp_path / "output.myst"
    generate_myst(test_data, output)
    
    content = output.read_text()
    assert "[List[Dict[str, int]]](#list)" in content
    assert "[Optional[float]](#optional)" in content 