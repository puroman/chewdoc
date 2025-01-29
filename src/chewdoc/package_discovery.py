from pathlib import Path
from typing import List, Dict
from .config import ChewdocConfig
import fnmatch

def get_package_name(pkg_path: Path) -> str:
    """
    Extract package name from directory structure with advanced heuristics.
    
    Args:
        pkg_path (Path): Path to the package directory
    
    Returns:
        str: Extracted package name
    """
    parts = list(pkg_path.parts)
    
    # Updated skip list to be less aggressive
    skip_dirs = ['src', 'lib', 'site-packages', 'dist-packages']
    
    for part in reversed(parts):
        clean_part = part.split('-')[0].split('_')[0].split('v')[0]
        
        # Skip common non-package directories
        if clean_part in skip_dirs:
            continue
        
        if clean_part and clean_part.replace('_', '').isalnum():
            # Prefer original part before any splitting
            if '_' in part or '-' in part:
                return part.split('.')[0]  # Handle versioned directories
            
            # Check parent directories for compound names
            parent_names = [p for p in parts if p not in skip_dirs]
            if len(parent_names) > 1:
                return '.'.join(parent_names[-2:])
            
            return clean_part
    
    return parts[-1]

def _is_namespace_package(pkg_path: Path) -> bool:
    """Detect namespace packages (PEP 420/PEP 451) with multiple detection strategies."""
    init_file = pkg_path / "__init__.py"
    
    # PEP 420 implicit namespace package (no __init__.py)
    if not init_file.exists():
        return True
    
    # Check for explicit namespace package markers
    try:
        content = init_file.read_text()
        namespace_markers = [
            "pkgutil.extend_path",
            "pkg_resources.declare_namespace",
            "__path__ = __import__('pkgutil').extend_path(__path__, __name__)"
        ]
        
        # Check for namespace markers
        if any(marker in content for marker in namespace_markers):
            return True
        
        # Empty or minimal __init__.py
        if not content.strip():
            return True
        
        # Check for typical namespace package content
        lines = content.split('\n')
        non_comment_lines = [line for line in lines if not line.strip().startswith('#')]
        
        # If no meaningful content beyond version or docstring, consider it a namespace package
        meaningful_lines = [line for line in non_comment_lines if not (
            line.strip().startswith(('__version__', '"""', "'''", 'from ', 'import ')) or
            line.strip() == ''
        )]
        
        return len(meaningful_lines) <= 0
    except Exception:
        # If file cannot be read, consider it a potential namespace package
        return True

def find_python_packages(root_dir: Path, config: ChewdocConfig) -> List[dict]:
    """Find Python packages with improved detection."""
    packages = []
    
    for path in root_dir.rglob("*/__init__.py"):
        if _is_excluded(path, config):
            continue
            
        pkg_path = path.parent
        full_pkg_name = _build_full_pkg_name(pkg_path, root_dir)
        
        if not full_pkg_name:
            continue
        
        packages.append({
            "name": full_pkg_name,
            "path": str(pkg_path),
            "is_namespace": _is_namespace_package(pkg_path)
        })
    
    return sorted(packages, key=lambda x: x["name"])

def _build_full_pkg_name(pkg_path: Path, root_dir: Path) -> str:
    """Construct full package name from path hierarchy"""
    parts = []
    current_path = pkg_path
    
    while current_path != root_dir.parent:  # Include immediate parent of root_dir
        part = get_package_name(current_path)
        if part and part not in parts:
            parts.insert(0, part)
        current_path = current_path.parent
    
    return '.'.join(parts) if parts else get_package_name(pkg_path)

def _is_excluded(path: Path, config: ChewdocConfig) -> bool:
    """Check if path matches any exclude patterns"""
    exclude_patterns = config.exclude_patterns  # Access list directly
    str_path = str(path.resolve())
    return any(fnmatch.fnmatch(str_path, pattern) for pattern in exclude_patterns) 