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
                if not _should_exclude(p, config.exclude_patterns):
                    packages.append({
                        "name": pkg_name,
                        "path": str(p),
                        "is_namespace": _is_namespace_package(p)
                    })
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
    
    return '.'.join(parts) if parts else get_package_name(pkg_path)

def _is_excluded(path: Path, config: ChewdocConfig) -> bool:
    """Check if path matches any exclude patterns"""
    exclude_patterns = config.exclude_patterns  # Access list directly
    str_path = str(path.resolve())
    return any(fnmatch.fnmatch(str_path, pattern) for pattern in exclude_patterns) 