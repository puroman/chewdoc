# Package metadata handling
from pathlib import Path
import subprocess
import tempfile
import tomllib
from typing import Dict, Optional, Any
from datetime import datetime


def get_package_metadata(path: Path, is_local: bool, version: str = "0.0.0") -> dict:
    """Get package metadata from local path or PyPI"""
    meta = {
        "name": path.name,
        "version": version,
        "source": "local" if is_local else "pypi",
        "timestamp": datetime.now().isoformat(),
    }

    if not is_local:
        try:
            pypi_meta = get_pypi_metadata(path.name)
            meta.update(pypi_meta)
        except Exception as e:
            logger.warning(f"Couldn't fetch PyPI metadata: {str(e)}")

    return meta


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
            "python_requires": ">=3.8",
        }
    except subprocess.CalledProcessError as e:
        raise ValueError(f"PyPI package {name} not found") from e


def _download_pypi_package(package_name: str, temp_dir: Path) -> Path:
    """Placeholder for PyPI package download functionality"""
    raise NotImplementedError("Remote package analysis is not yet implemented")
