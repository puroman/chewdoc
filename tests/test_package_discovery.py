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
