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
    assert ":::{module} testmod" in content
    assert "- os" in content
    assert "- sys" in content 

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
                "cross_references": {"MyType", "external.Type"},
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
    assert "- `os`" in content
    assert "## Module Dependencies" in content 

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
    assert "No internal dependencies" in content
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
    assert "version: 0.0.0" in content
    assert "author: Unknown Author" in content 

def test_class_formatting(tmp_path):
    test_data = {
        "modules": [{
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
    assert ":::TestClass" in output.read_text() 