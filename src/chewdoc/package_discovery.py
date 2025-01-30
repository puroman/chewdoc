from pathlib import Path
from typing import List, Dict, Optional
from .config import ChewdocConfig
import fnmatch
import re


def get_package_name(package_path: Path) -> Optional[str]:
    """Robust package name detection with versioned path handling"""
    version_pattern = re.compile(r"[-_]v?(\d+([.-]\d+)*)([.-]|$)")
    
    # Check parent directory for version pattern
    parent_name = package_path.parent.name
    parent_match = version_pattern.search(parent_name)
    if parent_match:
        base_name = re.sub(r"[-_]\d+.*", "", parent_name)
        return f"{base_name}.{package_path.name}"
    
    # Then check current directory name
    self_match = version_pattern.search(package_path.name)
    if self_match:
        return package_path.name[:self_match.start()].replace("_", "-")
    
    # Existing fallback logic...
    for parent in package_path.parents:
        if (parent / "__init__.py").exists():
            return parent.name
    return package_path.name


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


def find_python_packages(path: Path, config: ChewdocConfig) -> list:
    """Find Python packages in directory with better pattern matching"""
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


def _is_package_dir(path: Path, config: ChewdocConfig) -> bool:
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


def _is_excluded(path: Path, config: ChewdocConfig) -> bool:
    """Check if path matches any exclude patterns"""
    exclude_patterns = config.exclude_patterns  # Access list directly
    str_path = str(path.resolve())
    return any(fnmatch.fnmatch(str_path, pattern) for pattern in exclude_patterns)
