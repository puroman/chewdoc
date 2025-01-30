import re
from pathlib import Path
from typing import Optional

def get_package_name(package_path: Path) -> Optional[str]:
    """Robust package name detection with versioned path handling"""
    version_pattern = re.compile(r"-\d+\.\d+\.\d+")  # Match semantic version patterns
    
    # Check current directory first
    if match := version_pattern.search(package_path.name):
        return package_path.name[:match.start()].replace("_", "-")
    
    # Check parent directories up to 3 levels deep
    depth = 0
    for parent in package_path.parents:
        if depth > 3:  # Limit search depth
            break
        if match := version_pattern.search(parent.name):
            return parent.name[:match.start()].replace("_", "-")
        depth += 1
    
    return package_path.name.replace("_", "-")

def _build_full_pkg_name(pkg_path: Path, root_dir: Path) -> str:
    """Construct full package name from path hierarchy"""
    parts = []
    current_path = pkg_path.relative_to(root_dir).parent
    
    for part in current_path.parts:
        if part in ("src", "site-packages", "dist-packages"):
            continue
        clean_part = get_package_name(Path(part))
        parts.append(clean_part)
    
    # Add final package name
    parts.append(get_package_name(pkg_path))
    return ".".join(parts) 