import ast
from pathlib import Path
from src.chewdoc.core import _find_imports, _get_module_name, analyze_package
import pytest
from unittest.mock import Mock, patch
import subprocess
from unittest.mock import mock_open

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

def test_analyze_local_package():
    with patch("src.chewdoc.core._process_file") as mock_process, \
         patch("src.chewdoc.core.process_modules") as mock_modules, \
         patch("pathlib.Path.exists") as mock_exists:
        mock_exists.return_value = True
        mock_modules.return_value = [{
            "name": "testmod",
            "path": "tests/fixtures/valid_pkg/module.py"
        }]
        mock_process.return_value = {
            "name": "testmod",
            "path": str(Path("tests/fixtures/valid_pkg/module.py")),
            "ast": ast.Module(body=[]),
            "internal_deps": ["othermod"],
            "imports": [{"name": "sys", "type": "stdlib"}],
            "type_info": {
                "cross_references": set(),
                "functions": {},
                "classes": {},
                "variables": {}
            },
            "examples": [],
            "layer": "application",
            "role": "API interface",
            "constants": {},
            "docstrings": {}
        }
        
        result = analyze_package(
            source=str(Path("tests/fixtures/valid_pkg")),
            is_local=True,
            verbose=False
        )
        
        assert "testmod" in [m["name"] for m in result["modules"]]
        assert result["package"] == "valid_pkg"

def test_analyze_pypi_package():
    with patch("subprocess.run"), \
         patch("src.chewdoc.core._get_package_name") as mock_name, \
         patch("src.chewdoc.core.process_modules") as mock_modules, \
         patch("builtins.open", mock_open(read_data="def test(): pass")):
        mock_name.return_value = "requests"
        mock_modules.return_value = [{
            "name": "requests",
            "path": "/fake/requests.py",
            "internal_deps": [],
            "imports": [],
            "type_info": {"functions": {}, "classes": {}},
            "examples": [],
            "docstrings": {}
        }]
        
        result = analyze_package("requests", is_local=False)
        assert "requests" in result["package"]

def test_analyze_invalid_package():
    with pytest.raises(ValueError) as exc_info:
        analyze_package(source="/invalid/path", is_local=True)
    assert "Invalid source path" in str(exc_info.value)

def test_analyze_module_processing():
    with patch("src.chewdoc.core.process_modules") as mock_modules, \
         patch("builtins.open", mock_open(read_data="def test_func(): pass")):
        mock_modules.return_value = [{
            "name": "testmod",
            "path": "tests/fixtures/single_file.py"
        }]
        
        result = analyze_package(
            source="tests/fixtures/single_file.py",
            is_local=True,
            verbose=False
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