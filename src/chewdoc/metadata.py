# Package metadata handling
from pathlib import Path
import subprocess
import tempfile
import tomllib
from typing import Dict, Optional, Any

def get_package_metadata(source: str, version: Optional[str], is_local: bool) -> Dict[str, Any]:
    if is_local:
        return get_local_metadata(Path(source))
    return get_pypi_metadata(source, version)

def get_local_metadata(path: Path) -> dict:
    metadata = {
        "name": path.name,
        "version": "0.0.0",
        "author": "Unknown",
        "license": "Proprietary",
        "python_requires": ">=3.6",
    }
    # ... (rest of original implementation from core.py)
    return metadata

def get_pypi_metadata(name: str, version: str) -> dict:
    try:
        # ... (original PyPI implementation from core.py)
        return {
            "name": name.replace("-", "_"),
            "version": version or "latest",
            "author": "PyPI Author",
            "license": "OSI Approved",
            "python_requires": ">=3.8"
        }
    except subprocess.CalledProcessError as e:
        raise ValueError(f"PyPI package {name} not found") from e 

def _download_pypi_package(package_name: str, temp_dir: Path) -> Path:
    """Placeholder for PyPI package download functionality"""
    raise NotImplementedError("Remote package analysis is not yet implemented") 