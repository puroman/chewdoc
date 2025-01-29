from pathlib import Path
from typing import List, Dict
from .config import ChewdocConfig
import fnmatch

def find_python_packages(path: Path, config: ChewdocConfig) -> List[Dict]:
    """Find Python packages in directory with namespace support."""
    packages = []
    for dir_path in path.rglob("*/__init__.py"):
        pkg_path = dir_path.parent
        if _is_namespace_package(pkg_path):
            pkg_name = _get_package_name(pkg_path)
            if pkg_name and not _is_excluded(pkg_path, config.exclude_patterns):
                packages.append({
                    "name": pkg_name,
                    "path": str(pkg_path),
                    "is_namespace": True
                })
        else:
            pkg_name = _get_package_name(pkg_path)
            if pkg_name and not _is_excluded(pkg_path, config.exclude_patterns):
                packages.append({
                    "name": pkg_name,
                    "path": str(pkg_path),
                    "is_namespace": False
                })
    return packages

def _get_package_name(path: Path) -> str:
    """Extract package name from path."""
    parts = path.parts
    if "src" in parts:
        src_index = parts.index("src")
        return ".".join(parts[src_index+1:])
    return ".".join(parts[-2:]) if len(parts) > 1 else path.name

def _is_namespace_package(pkg_path: Path) -> bool:
    """Detect namespace packages (PEP 420/PEP 451)."""
    init_file = pkg_path / "__init__.py"
    if not init_file.exists():
        return True
    content = init_file.read_text()
    return "pkgutil" in content or "pkg_resources" in content

def _is_excluded(path: Path, exclude_patterns: List[str]) -> bool:
    """Check if path matches any exclusion patterns."""
    return any(fnmatch.fnmatch(str(path), pattern) for pattern in exclude_patterns) 