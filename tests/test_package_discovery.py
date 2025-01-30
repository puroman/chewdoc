from chewed.config import chewedConfig
from chewed.package_discovery import find_python_packages, _is_namespace_package
from pathlib import Path
import pytest
import os


def test_find_packages_with_symlinks(tmp_path):
    """Test package discovery with symlinks"""
    # Create original package
    pkg_dir = tmp_path / "original_pkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").touch()
    (pkg_dir / "module.py").write_text("def test(): pass")

    # Create symlink
    link_dir = tmp_path / "linked_pkg"
    os.symlink(pkg_dir, link_dir)

    config = chewedConfig()
    packages = find_python_packages(tmp_path, config)

    # Should only find one package (deduplicate symlinks)
    assert len([p for p in packages if p["name"] == "original_pkg"]) == 1


def test_find_python_packages_with_errors(tmp_path):
    """Test package discovery with problematic files"""
    pkg_dir = tmp_path / "test_pkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").touch()
    (pkg_dir / "good.py").write_text("def test(): pass")
    (pkg_dir / "bad.py").write_text("invalid python code {")

    config = chewedConfig()
    packages = find_python_packages(tmp_path, config)

    # Should find the package and good module despite the bad one
    assert len(packages) >= 2
    names = [p["name"] for p in packages]
    assert "test_pkg" in names
    assert "test_pkg.good" in names
