import pytest
from pathlib import Path
from src.chewdoc.core import (
    analyze_package,
    parse_pyproject,
    extract_docstrings,
    extract_type_info,
    download_pypi_package,
    _get_module_name,
    get_local_metadata,
    get_package_path,
    _get_package_name,
    _find_imports,
)
from src.chewdoc.config import ChewdocConfig
import ast
import subprocess
from unittest.mock import patch

@pytest.fixture
def config():
    return ChewdocConfig()

def test_analyze_local_package(tmp_path, config):
    pkg_dir = tmp_path / "testpkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text('"""Test package"""')
    (pkg_dir / "module.py").write_text('def test_fn():\n    """Test function"""')
    
    result = analyze_package(str(pkg_dir), is_local=True, config=config)
    assert result["name"] == "testpkg"
    assert len(result["modules"]) >= 1  # More reliable check


def test_pyproject_parsing(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
    [project]
    name = "testproj"
    version = "1.2.3"
    authors = [{name = "Test User"}]
    dependencies = ["requests>=2.0"]
    requires-python = ">=3.8"
    """
    )

    metadata = parse_pyproject(pyproject)
    assert metadata["name"] == "testproj"
    assert "requests>=2.0" in metadata["dependencies"]


def test_docstring_extraction(config):
    node = ast.parse("def func():\n    '''Docstring'''\n    pass")
    docstrings = extract_docstrings(node)
    assert "func:1" in docstrings
    assert docstrings["func:1"] == "Docstring"


def test_type_extraction(config):
    node = ast.parse("def func(a: int) -> bool:\n    b: str = 'text'")
    type_info = extract_type_info(node, config)
    assert type_info["functions"]["func"]["args"]["a"] == "int"


def test_type_cross_references(config):
    code = """\
class Item: pass
class Result: pass

def process(item: Item) -> Result:
    pass
"""
    node = ast.parse(code)
    type_info = extract_type_info(node, config)

    assert "Item" in type_info["cross_references"]
    assert "Result" in type_info["cross_references"]
    assert "process" in type_info["functions"]


def test_invalid_pypi_package():
    with pytest.raises(RuntimeError):
        analyze_package("nonexistent-package-1234", is_local=False)


def test_missing_local_package(tmp_path):
    with pytest.raises(RuntimeError):
        analyze_package(str(tmp_path / "missing"), is_local=True)


def test_empty_module_analysis(tmp_path):
    pkg_dir = tmp_path / "emptypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").touch()

    result = analyze_package(str(pkg_dir), is_local=True)
    assert len(result["modules"]) == 1
    assert not result["modules"][0]["docstrings"]


def test_package_download_failure(monkeypatch):
    def mock_run(*args, **kwargs):
        class FailedProcess:
            returncode = 1
            stderr = "Simulated download failure"

        return FailedProcess()

    monkeypatch.setattr(subprocess, "run", mock_run)

    with pytest.raises(RuntimeError):
        download_pypi_package("test-package")


def test_download_pypi_failure():
    with pytest.raises(RuntimeError), patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stderr="Not found"
        )
        download_pypi_package("invalid-package")


def test_download_no_files_found():
    with pytest.raises(FileNotFoundError), patch("subprocess.run") as mock_run, patch(
        "pathlib.Path.glob"
    ) as mock_glob:
        mock_run.return_value = subprocess.CompletedProcess([], 0)
        mock_glob.return_value = []
        download_pypi_package("empty-package")


def test_module_name_generation(tmp_path):
    pkg_root = tmp_path / "testpkg"
    pkg_root.mkdir()

    # Test regular module
    mod_file = pkg_root / "sub" / "module.py"
    mod_file.parent.mkdir()
    mod_file.touch()
    assert _get_module_name(mod_file, pkg_root) == "testpkg.sub.module"

    # Test __init__.py
    init_file = pkg_root / "__init__.py"
    init_file.touch()
    assert _get_module_name(init_file, pkg_root) == "testpkg"


def test_local_metadata_fallback(tmp_path):
    pkg_dir = tmp_path / "testpkg"
    pkg_dir.mkdir()
    (pkg_dir / "setup.py").touch()

    metadata = get_local_metadata(pkg_dir)
    assert metadata["name"] == "testpkg"


def test_missing_pypi_package():
    with pytest.raises(ValueError):
        get_package_path("nonexistent-pkg-123", is_local=False)


def test_docstring_extraction_error():
    bad_node = ast.parse("def test():\n    pass")
    bad_node.body[0].body = [
        ast.Expr(value=ast.Constant(value=123))
    ]  # Invalid docstring node
    assert extract_docstrings(bad_node) == {}


def test_package_extraction_logic(tmp_path):
    test_file = tmp_path / "test-1.0.0.tar.gz"
    test_file.touch()
    assert _get_package_name(test_file) == "test"


def test_pyproject_fallback(tmp_path):
    pkg_dir = tmp_path / "legacypkg"
    pkg_dir.mkdir()
    (pkg_dir / "setup.py").write_text(
        "from setuptools import setup\nsetup(name='legacy')"
    )

    metadata = get_local_metadata(pkg_dir)
    assert metadata["name"] == "legacy"
    assert metadata["version"] == "0.0.0"


def test_minimal_metadata(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.poetry]\nname = 'poetrypkg'")

    metadata = parse_pyproject(pyproject)
    assert metadata["name"] == "poetrypkg"
    assert metadata["author"] == "Unknown"


def test_import_discovery():
    code = """
import os
from pathlib import Path as P
import chewdoc.core
from . import submodule
"""
    node = ast.parse(code)
    imports = _find_imports(node)
    assert "os" in imports
    assert "chewdoc.core" in imports
    assert "submodule" in imports


def test_installed_package_path():
    with patch("importlib.metadata.distribution") as mock_dist:
        mock_dist.return_value.locate_file.return_value = Path("/fake/path")
        path = get_package_path("requests", False)
        assert str(path) == "/fake/path"


def test_nested_class_references(config):
    code = """\
class Outer:
    class Inner: pass

def process(o: Outer.Inner) -> None: pass
"""
    node = ast.parse(code)
    type_info = extract_type_info(node, config)

    assert "Outer.Inner" in type_info["cross_references"]
    assert "Outer" in type_info["cross_references"]


def test_constants_extraction(tmp_path):
    pkg_dir = tmp_path / "testpkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text('"""Test package"""')
    (pkg_dir / "module.py").write_text('def test_fn():\n    """Test function"""')
    (pkg_dir / "constants.py").write_text(
        'API_URL = "https://api.example.com"\n'
        'DEBUG = False\n'
        'class MyClass: pass\n'
    )
    result = analyze_package(str(pkg_dir), is_local=True)
    constants_module = next(m for m in result["modules"] if m["name"] == "testpkg.constants")
    
    # Updated assertions for dictionary format
    assert "API_URL" in constants_module["constants"]
    assert constants_module["constants"]["API_URL"]["value"] == '"https://api.example.com"'
    assert "DEBUG" in constants_module["constants"]
    assert constants_module["constants"]["DEBUG"]["value"] == "False"


def test_module_dependencies(tmp_path):
    pkg_dir = tmp_path / "testpkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text('"""Test package"""')
    (pkg_dir / "config.py").write_text('from .constants import DEFAULT_EXCLUSIONS')
    (pkg_dir / "constants.py").write_text('DEFAULT_EXCLUSIONS = [".venv"]')

    result = analyze_package(str(pkg_dir), is_local=True)
    config_module = next(m for m in result["modules"] if m["name"] == "testpkg.config")
    
    assert "testpkg.constants" in config_module["internal_deps"]
    assert "DEFAULT_EXCLUSIONS" not in config_module["internal_deps"]


def test_example_extraction(tmp_path):
    pkg_dir = tmp_path / "testpkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text('"""Test package"""')
    (pkg_dir / "examples.py").write_text('''
def example_function():
    """Example:
    >>> result = example_function()
    >>> print(result)
    42
    """
    return 42

def test_usage():
    assert example_function() == 42
''')

    result = analyze_package(str(pkg_dir), is_local=True)
    examples_module = next(m for m in result["modules"] if m["name"] == "testpkg.examples")
    
    assert len(examples_module["examples"]) == 2
    assert any(e["type"] == "doctest" for e in examples_module["examples"])
    assert any(e["type"] == "pytest" for e in examples_module["examples"])

def test_analyze_minimal_package(tmp_path, config):
    pkg_dir = tmp_path / "testpkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text('"""Package doc"""')
    (pkg_dir / "module.py").write_text('def func():\n    """Function doc"""')
    
    result = analyze_package(str(pkg_dir), is_local=True, config=config)
    assert result["name"] == "testpkg"
    assert any("module" in m["name"] for m in result["modules"])
