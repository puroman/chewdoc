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


def find_python_packages(package_path: Path, config: chewedConfig) -> List[Dict[str, str]]:
    """Find Python packages with improved versioned path handling"""
    packages = []
    
    # Normalize path and handle versioned directories
    package_path = package_path.resolve()
    
    # Check if the path itself is a package
    if _is_package(package_path, config):
        packages.append({
            "name": _derive_package_name(package_path),
            "path": str(package_path)
        })
    
    # Recursive package discovery
    for path in package_path.rglob("__init__.py"):
        pkg_dir = path.parent
        
        # Skip excluded paths
        if any(fnmatch.fnmatch(str(pkg_dir), pattern) for pattern in config.exclude_patterns):
            continue
        
        # Handle versioned paths
        pkg_name = _derive_package_name(pkg_dir)
        packages.append({
            "name": pkg_name,
            "path": str(pkg_dir)
        })
    
    return packages


def _derive_package_name(path: Path) -> str:
    """Derive package name from path, handling versioned directories"""
    # Remove version suffixes and normalize
    name = path.name.split('-')[0].split('_')[0]
    return re.sub(r'[.-]v?\d+.*', '', name).replace('-', '_').lower()


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
