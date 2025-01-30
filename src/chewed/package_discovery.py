from pathlib import Path
from typing import List, Dict, Optional
from .config import chewedConfig
import fnmatch
import re


def get_package_name(package_path: Path) -> str:
    """Robust package name extraction with version handling"""
    version_pattern = re.compile(r"[-_]v?\d+.*$")  # Match version suffix
    
    # Clean directory name
    dir_name = package_path.name
    clean_name = re.sub(version_pattern, "", dir_name)
    clean_name = re.sub(r"[-_.]+", "_", clean_name).lower()
    
    # Handle parent directory if current name is generic
    if clean_name in ("src", "lib", "site-packages", "dist-packages"):
        parent_name = package_path.parent.name
        clean_name = re.sub(version_pattern, "", parent_name)
        clean_name = re.sub(r"[-_.]+", "_", clean_name).lower()
    
    return clean_name or "unknown_package"


def _is_namespace_package(pkg_path: Path) -> bool:
    """Detect namespace packages more accurately"""
    init_file = pkg_path / "__init__.py"

    # PEP 420 namespace package
    if not init_file.exists():
        return True

    # Check for namespace declaration
    try:
        content = init_file.read_text()
        if "pkgutil" in content or "pkg_resources" in content:
            return True
    except UnicodeDecodeError:
        pass

    return False


def find_python_packages(path: Path, config: chewedConfig) -> list:
    """Find Python packages with configurable exclusion patterns"""
    packages = []

    # Match both regular and namespace packages
    for p in path.glob("**/"):
        if _is_package_dir(p, config):
            try:
                pkg_name = get_package_name(p)
                if not _is_excluded(p, config):
                    packages.append(
                        {
                            "name": pkg_name,
                            "path": str(p),
                            "is_namespace": _is_namespace_package(p),
                        }
                    )
            except ValueError:
                continue

    return packages


def _is_package_dir(path: Path, config: chewedConfig) -> bool:
    """Check if directory is a Python package"""
    # Allow namespace packages (no __init__.py) if configured
    if config.allow_namespace_packages:
        return True
    # Regular package must have __init__.py
    return (path / "__init__.py").exists()


def _build_full_pkg_name(pkg_path: Path, root_dir: Path) -> str:
    """Construct full package name from path hierarchy"""
    parts = []
    current_path = pkg_path

    while current_path != root_dir.parent:  # Include immediate parent of root_dir
        part = get_package_name(current_path)
        if part and part not in parts:
            parts.insert(0, part)
        current_path = current_path.parent

    return ".".join(parts) if parts else get_package_name(pkg_path)


def _is_excluded(path: Path, config: chewedConfig) -> bool:
    """Check if path matches any exclude patterns"""
    exclude_patterns = config.exclude_patterns  # Access list directly
    str_path = str(path.resolve())
    return any(fnmatch.fnmatch(str_path, pattern) for pattern in exclude_patterns)
