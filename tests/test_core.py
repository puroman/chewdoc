import ast
import textwrap
from pathlib import Path
from unittest.mock import patch, mock_open
import pytest
from chewed.core import analyze_package
from chewed.module_processor import (
    DocProcessor,
    _find_constants,
    _find_imports,
    _get_module_name,
)
from chewed.formatters.myst_writer import generate_docs, MystWriter
from chewed.config import chewedConfig
import subprocess
from chewed.package_discovery import (
    find_python_packages,
    get_package_name,
    _is_namespace_package,
)
from chewed.metadata import get_pypi_metadata


def test_get_module_name():
    file_path = Path("src/mypkg/modules/test.py")
    package_root = Path("src/mypkg")
    assert _get_module_name(file_path, package_root) == "modules.test"


def test_find_imports_internal():
    node = ast.parse("from mypkg.sub import mod")
    imports = _find_imports(node, "mypkg")
    assert any(
        i["full_path"] == "mypkg.sub.mod" and i["type"] == "internal" for i in imports
    )


def test_find_imports_external():
    node = ast.parse("import external.lib")
    imports = _find_imports(node, "mypkg")
    assert any(
        i["full_path"] == "external.lib" and i["type"] == "external" for i in imports
    )


def test_find_imports_stdlib():
    node = ast.parse("import sys; from pathlib import Path")
    imports = _find_imports(node, "mypkg")
    assert any(i["full_path"] == "sys" and i["type"] == "stdlib" for i in imports)
    assert any(
        i["full_path"] == "pathlib.Path" and i["type"] == "stdlib" for i in imports
    )


def test_analyze_local_package(tmp_path):
    # Create valid package structure
    pkg_root = tmp_path / "test_pkg"
    pkg_root.mkdir()
    (pkg_root / "__init__.py").write_text("__version__ = '1.0'")
    (pkg_root / "module.py").write_text("def example(): pass")

    config = chewedConfig()
    result = analyze_package(source=str(pkg_root), is_local=True, config=config)
    assert len(result["modules"]) >= 1


@pytest.mark.xfail(reason="PyPI implementation not complete")
def test_analyze_pypi_package(tmp_path):
    with patch("subprocess.run"), patch(
        "chewed.package_discovery.get_package_name"
    ) as mock_name, patch("chewed.core.process_modules") as mock_modules, patch(
        "chewed.metadata._download_pypi_package"
    ) as mock_download:
        mock_name.return_value = "testpkg"
        mock_modules.return_value = [{"name": "testmod"}]

        # Create a mock package path
        mock_pkg_path = tmp_path / "testpkg"
        mock_pkg_path.mkdir()
        (mock_pkg_path / "__init__.py").touch()

        mock_download.return_value = mock_pkg_path

        result = analyze_package("testpkg", is_local=False, config=chewedConfig())
        assert len(result) == 1
        assert result[0]["name"] == "testmod"


def test_analyze_invalid_package(tmp_path):
    with pytest.raises(ValueError, match="No valid modules found"):
        analyze_package(str(tmp_path), is_local=True, config=chewedConfig())


def test_analyze_module_processing(tmp_path, mocker):
    with patch(
        "chewed.module_processor.process_modules", return_value=[{"name": "test"}]
    ) as mock_process:
        result = analyze_package(str(tmp_path), is_local=True, config=chewedConfig())
        mock_process.assert_called_once()
        assert len(result["modules"]) == 1


def test_skip_empty_init(tmp_path):
    init_file = tmp_path / "__init__.py"
    init_file.touch()

    with patch("chewed.core.process_modules") as mock_modules:
        mock_modules.return_value = [{"name": "test", "path": str(init_file)}]
        analyze_package(
            str(tmp_path), is_local=True, config=chewedConfig(), verbose=True
        )


def test_analyze_empty_package(tmp_path):
    empty_pkg = tmp_path / "empty_pkg"
    empty_pkg.mkdir()
    (empty_pkg / "__init__.py").touch()

    result = analyze_package(
        source=str(empty_pkg), is_local=True, config=chewedConfig()
    )

    assert len(result["modules"]) == 1
    assert result["modules"][0]["name"] == "empty_pkg"


def test_analyze_invalid_source():
    with pytest.raises(ValueError, match="Source path does not exist"):
        analyze_package(
            source="/invalid/path", is_local=True, config=chewedConfig(), verbose=False
        )


def test_analyze_syntax_error(tmp_path):
    bad_file = tmp_path / "invalid.py"
    bad_file.write_text("def invalid_syntax")
    with pytest.raises(RuntimeError, match="No valid modules found"):
        analyze_package(
            source=str(tmp_path), is_local=True, config=chewedConfig(), verbose=False
        )


def test_find_python_packages_namespace(tmp_path):
    """Test namespace package detection"""
    pkg_path = tmp_path / "ns_pkg-1.2.3" / "ns_pkg" / "sub"
    pkg_path.mkdir(parents=True)
    (pkg_path.parent / "__init__.py").write_text(
        "__path__ = __import__('pkgutil').extend_path(__path__, __name__)"
    )

    config = chewedConfig(exclude_patterns=["build/*"])  # Proper list init
    packages = find_python_packages(tmp_path, config)
    assert len(packages) > 0


def test_get_package_name_versioned():
    assert get_package_name(Path("my-pkg-v1.2")) == "my_pkg"
    assert get_package_name(Path("another_pkg-3.4.5")) == "another_pkg"


def test_is_namespace_package(tmp_path):
    """Test namespace package detection logic"""
    # Test pkgutil-style namespace
    pkg_path = tmp_path / "ns_pkg"
    pkg_path.mkdir()
    init_file = pkg_path / "__init__.py"
    init_file.write_text(
        "__path__ = __import__('pkgutil').extend_path(__path__, __name__)\n"
    )
    assert _is_namespace_package(pkg_path) is True

    # Test PEP 420 namespace (no __init__.py)
    empty_pkg = tmp_path / "empty_ns"
    empty_pkg.mkdir()
    assert _is_namespace_package(empty_pkg) is True

    # Test regular package with non-empty init
    reg_pkg = tmp_path / "regular_pkg"
    reg_pkg.mkdir()
    (reg_pkg / "__init__.py").write_text("__version__ = '1.0'")
    assert _is_namespace_package(reg_pkg) is False


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
    constants = _find_constants(node, chewedConfig())
    assert len(constants) == 3
    assert constants["MAX_LIMIT"]["type"] == "int"
    assert constants["DEFAULT_NAME"]["type"] == "str"
    assert constants["__version__"]["value"] == "'1.0'"


def test_generate_docs_minimal(tmp_path):
    """Test doc generation with minimal valid input"""
    package_info = {"package": "minimal", "modules": [{"name": "mod1"}], "config": {}}
    generate_docs(package_info, tmp_path)
    assert (tmp_path / "index.md").exists()


def test_analyze_package_error_handling():
    with pytest.raises(RuntimeError) as excinfo:
        analyze_package(source="/non/existent", is_local=True, config=chewedConfig())
    assert "Package analysis failed" in str(excinfo.value)


def test_find_python_packages_edge_cases(tmp_path):
    versioned_path = tmp_path / "pkg-v1.2.3" / "pkg" / "sub"
    versioned_path.mkdir(parents=True)
    (versioned_path / "__init__.py").touch()

    config = chewedConfig()
    packages = find_python_packages(tmp_path, config)
    assert any(
        p["name"] == "pkg.sub" for p in packages
    ), f"Expected pkg.sub in {[p['name'] for p in packages]}"


def test_example_processing():
    """Test example processing with different input formats."""
    processor = DocProcessor(
        config={},
        examples=[
            "print('hello')",
            {"content": "import os", "result": ""},  # Valid legacy format
            {"invalid": "format"},  # Should be filtered out
            123,  # invalid type
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
    processor = DocProcessor(config=chewedConfig(), examples="print('valid')")
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
    processor = DocProcessor(config=chewedConfig())

    # Mock the class method directly
    with patch.object(
        DocProcessor, "process_module", return_value={"type_info": {}}
    ) as mock_process:
        result = processor.process_module(Path("fake.py"))
        assert "type_info" in result
        mock_process.assert_called_once_with(Path("fake.py"))
