import ast
import textwrap
from pathlib import Path
from unittest.mock import patch, mock_open
import pytest
from src.chewdoc.core import (
    analyze_package,
    find_python_packages,
    is_namespace_package,
    _get_package_name,
    _find_constants,
    DocProcessor,
    _find_imports,
    _get_module_name,
)
from src.chewdoc.formatters.myst_writer import generate_docs, MystWriter
from src.chewdoc.config import ChewdocConfig
import subprocess


def test_get_module_name():
    file_path = Path("src/mypkg/modules/test.py")
    package_root = Path("src/mypkg")
    assert _get_module_name(file_path, package_root) == "modules.test"


def test_find_imports_internal():
    node = ast.parse("from mypkg.sub import mod")
    imports = _find_imports(node, "mypkg")
    assert any(i["full_path"] == "sub.mod" and i["type"] == "internal" for i in imports)


def test_find_imports_external():
    node = ast.parse("import external.lib")
    imports = _find_imports(node, "mypkg")
    assert any(i["name"] == "external.lib" and i["type"] == "external" for i in imports)


def test_find_imports_stdlib():
    node = ast.parse("import sys")
    imports = _find_imports(node, "mypkg")
    assert any(i["name"] == "sys" and i["type"] == "stdlib" for i in imports)


def test_analyze_local_package(tmp_path, mocker):
    # Create valid package structure
    pkg_root = tmp_path / "test_pkg"
    pkg_root.mkdir()
    (pkg_root / "__init__.py").touch()
    (pkg_root / "module.py").write_text("def example(): pass")

    # Mock dependencies
    mock_process = mocker.patch("src.chewdoc.core.process_modules")
    mock_process.return_value = [
        {
            "name": "test_pkg.module",
            "path": str(pkg_root / "module.py"),
            "docstrings": {"module": "Test module"},
        }
    ]

    result = analyze_package(source=str(pkg_root), is_local=True)

    assert "test_pkg" in result["package"]
    assert len(result["modules"]) == 1
    assert result["modules"][0]["name"] == "test_pkg.module"


def test_analyze_pypi_package():
    with patch("subprocess.run"), \
         patch("src.chewdoc.core._get_package_name") as mock_name, \
         patch("src.chewdoc.core.process_modules") as mock_modules, \
         patch("src.chewdoc.core.get_pypi_metadata") as mock_metadata, \
         patch("src.chewdoc.core.get_package_path") as mock_pkg_path, \
         patch("builtins.open", mock_open(read_data="def test(): pass")):
        
        # Setup mocks
        mock_name.return_value = "requests"
        mock_metadata.return_value = {
            "name": "requests",
            "version": "2.28.2",
            "author": "Kenneth Reitz",
            "license": "Apache 2.0",
            "python_requires": ">=3.7",
            "dependencies": ["urllib3>=1.26"]
        }
        mock_pkg_path.return_value = Path("/mock/pypi/requests")
        mock_modules.return_value = [
            {
                "name": "requests",
                "path": "/fake/requests.py",
                "internal_deps": [],
                "imports": [],
                "type_info": {"functions": {}, "classes": {}},
                "examples": [],
                "docstrings": {},
            }
        ]

        result = analyze_package("requests", is_local=False)
        assert result["metadata"]["name"] == "requests"
        assert result["metadata"]["version"] == "2.28.2"
        assert "dependencies" in result["metadata"]


def test_analyze_invalid_package():
    with pytest.raises(ValueError) as exc_info:
        analyze_package(source="/invalid/path", is_local=True)
    assert "Invalid source path" in str(exc_info.value)


def test_analyze_module_processing():
    with patch("src.chewdoc.core.process_modules") as mock_modules, patch(
        "builtins.open", mock_open(read_data="def test_func(): pass")
    ):
        mock_modules.return_value = [
            {"name": "testmod", "path": "tests/fixtures/single_file.py"}
        ]

        result = analyze_package(
            source="tests/fixtures/single_file.py", is_local=True, verbose=False
        )

        assert "test_func" in result["modules"][0]["type_info"]["functions"]


def test_skip_empty_init(tmp_path):
    init_file = tmp_path / "__init__.py"
    init_file.touch()

    with patch("src.chewdoc.core.process_modules") as mock_modules:
        mock_modules.return_value = [{"name": "test", "path": str(init_file)}]
        result = analyze_package(str(tmp_path), is_local=True, verbose=True)

    assert len(result["modules"]) == 0


def test_analyze_empty_package(tmp_path):
    empty_pkg = tmp_path / "empty_pkg"
    empty_pkg.mkdir()
    (empty_pkg / "__init__.py").touch()

    with patch("src.chewdoc.core.process_modules") as mock_process:
        mock_process.return_value = []
        with pytest.raises(RuntimeError) as exc_info:
            analyze_package(source=str(empty_pkg), is_local=True)
        assert "No valid modules found" in str(exc_info.value)


def test_analyze_invalid_source():
    with pytest.raises(ValueError) as exc_info:
        analyze_package(source="/invalid/path", is_local=True)
    assert "Invalid source path" in str(exc_info.value)


def test_analyze_syntax_error(tmp_path):
    bad_file = tmp_path / "invalid.py"
    bad_file.write_text("def invalid_syntax")
    with pytest.raises(RuntimeError) as exc_info:
        analyze_package(source=str(tmp_path), is_local=True)
    assert "No valid modules found" in str(exc_info.value)


def test_find_python_packages_namespace(tmp_path):
    """Test namespace package detection"""
    pkg_path = tmp_path / "ns_pkg-1.2.3" / "ns_pkg" / "sub"
    pkg_path.mkdir(parents=True)
    (pkg_path / "__init__.py").write_text("")

    config = ChewdocConfig()
    packages = find_python_packages(tmp_path, config)
    assert any(p["name"] == "ns_pkg.sub" for p in packages)


def test_get_package_name_versioned(tmp_path):
    versioned_path = tmp_path / "my-pkg-1.2.3" / "src" / "my_pkg"
    versioned_path.mkdir(parents=True)
    assert _get_package_name(versioned_path) == "my_pkg"


def test_is_namespace_package(tmp_path):
    """Test namespace package detection logic"""
    # Test pkgutil-style namespace
    pkg_path = tmp_path / "ns_pkg"
    pkg_path.mkdir()
    init_file = pkg_path / "__init__.py"
    init_file.write_text(
        "__path__ = __import__('pkgutil').extend_path(__path__, __name__)\n"
    )
    assert is_namespace_package(pkg_path) is True

    # Test PEP 420 namespace (no __init__.py)
    empty_pkg = tmp_path / "empty_ns"
    empty_pkg.mkdir()
    assert is_namespace_package(empty_pkg) is True

    # Test regular package with non-empty init
    reg_pkg = tmp_path / "regular_pkg"
    reg_pkg.mkdir()
    (reg_pkg / "__init__.py").write_text("__version__ = '1.0'")
    assert is_namespace_package(reg_pkg) is False


def test_find_constants():
    """Test constant finding with type inference"""
    node = ast.parse(
        textwrap.dedent(
            """
        MAX_LIMIT = 100
        DEFAULT_NAME: str = 'test'
        __version__ = '1.0'
    """
        )
    )
    constants = _find_constants(node, ChewdocConfig())
    assert len(constants) == 3
    assert constants["MAX_LIMIT"]["type"] == "int"
    assert constants["DEFAULT_NAME"]["type"] == "str"
    assert constants["__version__"]["value"] == "'1.0'"


def test_generate_docs_minimal(tmp_path):
    """Test doc generation with minimal valid input"""
    package_info = {"package": "minimal", "modules": [{"name": "mod1"}], "config": {}}
    generate_docs(package_info, tmp_path)
    assert (tmp_path / "index.md").exists()


def test_analyze_package_error_handling(tmp_path):
    """Test error handling in package analysis"""
    test_path = tmp_path / "valid_path"
    test_path.mkdir()

    with patch("pathlib.Path.exists") as mock_exists, patch(
        "src.chewdoc.core.process_modules"
    ) as mock_process:
        mock_exists.return_value = True
        mock_process.side_effect = RuntimeError("Simulated failure")
        with pytest.raises(RuntimeError):
            analyze_package(str(test_path), is_local=True)


def test_find_python_packages_edge_cases(tmp_path):
    """Test package finding with unusual directory structures"""
    # Test versioned parent directory
    versioned_path = tmp_path / "pkg-v1.2.3" / "pkg" / "sub"
    versioned_path.mkdir(parents=True)
    (versioned_path / "__init__.py").write_text("")
    config = ChewdocConfig()
    packages = find_python_packages(tmp_path, config)
    assert any(p["name"] == "pkg.sub" for p in packages)


def test_example_processing():
    """Test example processing with different input formats."""
    processor = DocProcessor(
        config={},
        examples=[
            "print('hello')",
            {"content": "import os", "result": ""},  # Valid legacy format
            {"invalid": "format"},  # Should be filtered out
            123  # invalid type
        ],
    )
    
    assert len(processor.examples) == 2
    assert processor.examples[0]["code"] == "print('hello')"
    assert processor.examples[1]["code"] == "import os"


def test_error_handling():
    """Test invalid example handling."""
    processor = DocProcessor(config={}, examples=[{"invalid": "format"}, 12345])
    assert len(processor.examples) == 0


def test_edge_case_examples():
    """Test non-standard but valid example formats."""
    processor = DocProcessor(
        config={},
        examples=[
            {"content": "import os", "result": ""},  # Legacy format
            {"code": 42, "output": None},  # Non-string values
        ],
    )
    
    assert len(processor.examples) == 2
    assert processor.examples[0]["code"] == "import os"
    assert processor.examples[1]["code"] == "42"


def test_config_example_types():
    """Test config validation handles different example container types"""
    processor = DocProcessor(config=ChewdocConfig(), examples="print('valid')")
    assert len(processor.examples) == 1
    assert processor.examples[0]["code"] == "print('valid')"


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

    # Should not raise an error now
    writer.generate(package_info, tmp_path)
    content = (tmp_path / "broken_mod.md").read_text()
    assert "## `bad_func()" in content


def test_process_invalid_module():
    """Test module processing with invalid AST"""
    processor = DocProcessor(config=ChewdocConfig())
    
    # Mock the class method directly
    with patch.object(DocProcessor, 'process_module', return_value={"type_info": {}}) as mock_process:
        result = processor.process_module(Path("fake.py"))
        assert "type_info" in result
        mock_process.assert_called_once_with(Path("fake.py"))
