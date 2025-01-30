from pathlib import Path
from typing import List, Dict, Optional
from .config import chewedConfig
import fnmatch
import re
import os


def get_package_name(package_path: Path) -> str:
    """Robust package name extraction with version handling"""
    version_pattern = re.compile(r"[-_]v?\d+.*$")  # Match version suffix

    # Clean directory name
    dir_name = package_path.name

    # Check parent directory if current dir is versioned
    parent = package_path.parent
    if version_pattern.search(dir_name) and parent.name != package_path.name:
        parent_clean = re.sub(version_pattern, "", parent.name)
        if parent_clean:
            return re.sub(r"[-_.]+", "_", parent_clean).lower()

    # Original cleaning logic
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


def find_python_packages(
    package_path: Path, config: chewedConfig
) -> List[Dict[str, str]]:
    """Find Python packages with improved path handling"""
    packages = []

    # Handle root package first
    if _is_package(package_path, config):
        packages.append(
            {
                "name": _derive_package_name(package_path),
                "path": str(package_path.resolve()),
            }
        )

    # Recursive discovery with proper path resolution
    for path in package_path.resolve().rglob("__init__.py"):
        pkg_dir = path.parent

        # Skip excluded paths using resolved paths
        resolved_pkg = pkg_dir.resolve()
        if any(
            fnmatch.fnmatch(str(resolved_pkg), pattern)
            for pattern in config.exclude_patterns
        ):
            continue

        # Handle versioned paths and nested packages
        pkg_name = _derive_nested_package_name(resolved_pkg, package_path.resolve())
        packages.append({"name": pkg_name, "path": str(resolved_pkg)})

    return packages


def _derive_nested_package_name(pkg_dir: Path, root_path: Path) -> str:
    """Derive package name for nested packages with proper path handling"""
    try:
        # Compute relative path from root using resolved paths
        relative_path = pkg_dir.relative_to(root_path.resolve())

        # Convert path to package name
        pkg_name = ".".join(part.replace("-", "_") for part in relative_path.parts)

        # Remove version suffixes but preserve dots
        pkg_name = re.sub(r"[-_]v?\d+[\d_.]*(?=\.|$)", "", pkg_name)
        
        return pkg_name.lower()
    except ValueError:
        return _derive_package_name(pkg_dir)


def _derive_package_name(path: Path) -> str:
    """Derive package name from path, handling versioned directories"""
    # Remove version suffixes and normalize
    name = path.name.split("-")[0].split("_")[0]
    clean_name = re.sub(r"[.-]v?\d+.*", "", name).replace("-", "_").lower()

    # Handle special case directories
    if clean_name in ["src", "lib", "site-packages", "dist-packages"]:
        parent_name = path.parent.name
        clean_name = re.sub(r"[.-]v?\d+.*", "", parent_name).replace("-", "_").lower()

    return clean_name or "unknown_package"


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


def _is_package(path: Path, config: chewedConfig) -> bool:
    """Determine if a path is a valid Python package"""
    # Check for basic package structure
    if not any(path.glob("*.py")) and not config.allow_namespace_packages:
        return False
        
    # Check for __init__.py if namespace packages are not allowed
    if not config.allow_namespace_packages:
        return (path / "__init__.py").exists()

    # For namespace packages, check for __init__.py or allow empty directories
    init_py = path / "__init__.py"
    return init_py.exists() or config.namespace_fallback
