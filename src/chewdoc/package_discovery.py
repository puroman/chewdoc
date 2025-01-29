from pathlib import Path
from typing import List, Dict
from .config import ChewdocConfig

def find_python_packages(root_path: Path, config: ChewdocConfig) -> List[Dict]:
    """Find Python packages in directory."""
    packages = []
    for path in root_path.rglob("*/__init__.py"):
        if _is_namespace_package(path.parent):
            pkg_type = "namespace"
        else:
            pkg_type = "regular"
            
        packages.append({
            "name": _get_package_name(path.parent),
            "path": str(path.parent),
            "type": pkg_type
        })
    return packages

def _get_package_name(path: Path) -> str:
    """Extract package name from path."""
    parts = path.parts
    if "src" in parts:
        return parts[parts.index("src") + 1]
    return path.name

def _is_namespace_package(pkg_path: Path) -> bool:
    """Detect namespace packages (PEP 420/PEP 451)."""
    init_file = pkg_path / "__init__.py"
    if not init_file.exists():
        return True
    content = init_file.read_text()
    return "pkgutil" in content or "pkg_resources" in content 