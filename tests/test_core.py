import pytest
from pathlib import Path
from src.chewdoc.core import analyze_package, parse_pyproject, extract_docstrings, extract_type_info, download_pypi_package, _get_module_name
import ast
import subprocess
from unittest.mock import patch

def test_analyze_local_package(tmp_path):
    # Create test package structure
    pkg_dir = tmp_path / "testpkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text('"""Test package"""')
    (pkg_dir / "module.py").write_text('def test_fn():\n    """Test function"""')
    
    result = analyze_package(str(pkg_dir), is_local=True)
    
    # Find the module.py entry safely
    modules = [m for m in result["modules"] if m["name"] == "testpkg.module"]
    assert len(modules) == 1, "Expected exactly one testpkg.module"
    module = modules[0]
    
    # Verify function exists in AST
    assert any(
        isinstance(n, ast.FunctionDef) and n.name == "test_fn"
        for n in ast.walk(module["ast"])
    ), "test_fn function not found in AST"

def test_pyproject_parsing(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("""
    [project]
    name = "testproj"
    version = "1.2.3"
    authors = [{name = "Test User"}]
    dependencies = ["requests>=2.0"]
    requires-python = ">=3.8"
    """)
    
    metadata = parse_pyproject(pyproject)
    assert metadata["name"] == "testproj"
    assert "requests>=2.0" in metadata["dependencies"]

def test_docstring_extraction():
    code = '''\
def test_fn():
    """Test docstring"""
    pass
'''
    node = ast.parse(code)
    docstrings = extract_docstrings(node)
    assert "Test docstring" in docstrings.values()

def test_type_hint_extraction():
    code = '''\
def test(a: int) -> bool:
    b: str = "test"
'''
    node = ast.parse(code)
    type_info = extract_type_info(node)
    
    assert type_info["functions"]["test"]["args"]["a"] == "int"
    assert type_info["functions"]["test"]["returns"] == "bool"
    assert type_info["variables"]["b"] == "str"

def test_type_cross_references():
    code = '''\
class Item: pass
class Result: pass

def process(item: Item) -> Result:
    pass
'''
    node = ast.parse(code)
    type_info = extract_type_info(node)
    
    assert "Item" in type_info["cross_references"]
    assert "Result" in type_info["cross_references"]
    assert "process" in type_info["functions"]

def test_invalid_pypi_package():
    with pytest.raises(RuntimeError) as exc_info:
        analyze_package("nonexistent-package-1234", is_local=False)
    assert "Package nonexistent-package-1234 not found in PyPI" in str(exc_info.value)

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
    with pytest.raises(RuntimeError), \
         patch('subprocess.run') as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stderr="Not found"
        )
        download_pypi_package("invalid-package")

def test_download_no_files_found():
    with pytest.raises(FileNotFoundError), \
         patch('subprocess.run') as mock_run, \
         patch('pathlib.Path.glob') as mock_glob:
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