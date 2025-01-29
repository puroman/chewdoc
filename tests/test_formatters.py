from src.chewdoc.formatters.myst_writer import MystWriter
from pathlib import Path
import ast
import pytest
from chewdoc.config import ChewdocConfig


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
                            "returns": ast.Name(id="str"),
                        }
                    },
                    "cross_references": ["othermod"],
                },
            }
        ],
    }
    writer.generate(package_info, tmp_path)
    content = (tmp_path / "testmod.md").read_text()

    assert "### [[TestClass]]" in content
    assert "Class docstring" in content
    assert "#### Methods" in content
    assert "## `test_func(param) -> str`" in content


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
        "modules": [{
            "name": "broken_mod",
            "type_info": {
                "functions": {
                    "bad_func": {
                        "args": "invalid",
                        "returns": "str"
                    }
                }
            }
        }]
    }

    writer.generate(package_info, tmp_path)
    content = (tmp_path / "broken_mod.md").read_text()
    
    assert "bad_func()  # Unable to parse arguments" in content


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
    assert "Expected dict or string" in caplog.text
    assert "Expected dict with 'code' or 'content' key" in caplog.text


def test_myst_writer_config_initialization():
    """Test MystWriter config handling"""
    writer = MystWriter()
    assert writer.config.max_example_lines == 10
    
    custom_config = ChewdocConfig(max_example_lines=25)
    writer = MystWriter(config=custom_config)
    assert writer.config.max_example_lines == 25


def test_myst_writer_format_dependencies():
    """Test dependency formatting edge cases"""
    writer = MystWriter()
    
    # Test empty dependencies
    assert "No internal dependencies" in writer._format_dependencies([])
    
    # Test dependency cleaning
    deps = ["my.module", "another-module"]
    result = writer._format_dependencies(deps)
    assert "my_module" in result
    assert "another_module" in result


def test_myst_writer_format_metadata():
    """Test metadata formatting with missing fields"""
    writer = MystWriter()
    minimal_data = {"package": "testpkg"}
    result = writer._format_metadata(minimal_data)
    
    assert "testpkg" in result
    assert "0.0.0" in result  # Default version
    assert "Unknown Author" in result


def test_myst_writer_format_code_structure():
    """Test AST code structure formatting"""
    writer = MystWriter()
    
    from textwrap import dedent
    code = dedent("""
    class MyClass:
        def my_method(self):
            pass
    """)
    tree = ast.parse(code)
    result = writer._format_code_structure(tree)
    
    assert "Class: MyClass" in result
    assert "Method: my_method" in result


def test_myst_writer_format_imports_edge_cases():
    """Test import formatting with various scenarios"""
    writer = MystWriter()
    writer.current_module = {"type_info": {}}
    package = "testpkg"
    
    imports = [
        {"name": "os", "full_path": "os", "source": ""},
        {"name": "internal", "full_path": "testpkg.sub", "source": "testpkg.sub"},
        {"name": "numpy", "full_path": "numpy.array", "source": "numpy"},
    ]
    result = writer._format_imports(imports, package)
    
    assert "Standard Library" in result
    assert "Internal Dependencies" in result
    assert "External Dependencies" in result
    assert "numpy.array" in result


def test_myst_writer_format_module_error_handling():
    """Test error handling in module formatting"""
    writer = MystWriter()
    writer.package_data = {"package": "testpkg"}
    
    result = writer._format_module_content({
        "name": "bad_module",
        "type_info": {
            "functions": {
                "bad_func": {
                    "args": {"args": "not-a-list"},
                    "returns": "str"
                }
            }
        }
    })
    
    assert "bad_func" in result
    assert "Invalid arguments" in result


def test_myst_writer_example_validation():
    """Test example formatting with invalid entries"""
    writer = MystWriter()
    examples = [
        {"invalid": "structure"},
        12345,
        {"code": "valid = True"}
    ]
    
    result = writer._format_usage_examples(examples)
    assert "valid = True" in result
    assert "No examples available" not in result


def test_myst_writer_class_formatting():
    """Test class documentation formatting"""
    writer = MystWriter()
    class_info = {
        "doc": "Class documentation",
        "methods": {
            "my_method": {
                "args": ast.parse("def my_method(self): pass").body[0].args,
                "doc": "Method docs"
            }
        }
    }
    
    result = writer._format_class("MyClass", class_info)
    assert "MyClass" in result
    assert "my_method" in result


def test_myst_writer_variable_formatting(tmp_path):
    """Test variable formatting with different data types"""
    writer = MystWriter()
    package_info = {
        "package": "testpkg",
        "modules": [
            {
                "name": "var_module",
                "type_info": {
                    "variables": {
                        "STR_VAR": "hello",  # String value
                        "DICT_VAR": {"value": 42},  # Normal dict format
                        "INT_VAR": 100  # Direct value
                    }
                }
            }
        ]
    }
    
    writer.generate(package_info, tmp_path)
    content = (tmp_path / "var_module.md").read_text()
    
    assert "### Variables" in content
    assert "- `STR_VAR`: hello" in content
    assert "- `DICT_VAR`: 42" in content
    assert "- `INT_VAR`: 100" in content


def test_myst_writer_invalid_function_args(tmp_path):
    """Test handling of invalid function arguments"""
    writer = MystWriter()
    package_info = {
        "package": "testpkg",
        "modules": [
            {
                "name": "bad_args",
                "type_info": {
                    "functions": {
                        "broken_func": {
                            "args": {"invalid": "structure"},
                            "returns": "str"
                        }
                    }
                }
            }
        ]
    }
    
    # Should not raise an error
    writer.generate(package_info, tmp_path)
    content = (tmp_path / "bad_args.md").read_text()
    assert "broken_func()  # Error" in content


def test_format_empty_class():
    """Test class formatting with missing methods"""
    writer = MystWriter()
    result = writer._format_class("EmptyClass", {"doc": "No methods"})
    assert "EmptyClass" in result
    assert "No methods" in result


def test_format_function_with_ast_arguments():
    """Test function formatting with real AST arguments"""
    writer = MystWriter()
    func_ast = ast.parse("def test(a: int, b: str = '') -> bool: pass").body[0]
    
    result = writer._format_function("test", {
        "args": func_ast.args,
        "returns": func_ast.returns
    })
    
    assert "test(a: int, b: str = '') -> bool" in result
