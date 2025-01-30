# Package metadata handling
from pathlib import Path
import subprocess
import tempfile
import tomllib
from typing import Dict, Optional, Any
from datetime import datetime
import os
import requests


def get_package_metadata(
    source: str, 
    version: Optional[str] = None, 
    is_local: bool = True
) -> Dict[str, Any]:
    """
    Get package metadata for local or PyPI packages
    
    Args:
        source (str): Package source path or name
        version (Optional[str]): Package version
        is_local (bool): Whether source is local or from PyPI
    
    Returns:
        Dict[str, Any]: Package metadata
    """
    if is_local:
        path = Path(source)
        if not path.exists():
            raise ValueError(f"Local package path does not exist: {source}")
            
        return {
            "package": path.name,
            "path": str(path.resolve()),
            "version": version or "0.0.0",
            "python_requires": ">=3.8"
        }
    else:
        package_path = get_pypi_metadata(source, version)
        return {
            "package": source,
            "path": str(package_path),
            "version": version or "latest",
            "python_requires": ">=3.8"
        }


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


def get_pypi_metadata(package_name: str, version: Optional[str] = None) -> Path:
    """
    Download a package from PyPI and return its local path
    
    Args:
        package_name (str): Name of the package on PyPI
        version (Optional[str]): Specific version to download
    
    Returns:
        Path: Local path to downloaded package
    """
    try:
        # Fetch package metadata from PyPI
        url = f"https://pypi.org/pypi/{package_name}/json"
        response = requests.get(url)
        response.raise_for_status()
        
        package_data = response.json()
        
        # Determine version
        if not version:
            version = package_data['info']['version']
        
        # Find appropriate release
        releases = package_data['releases'].get(version, [])
        if not releases:
            raise ValueError(f"No release found for version {version}")
        
        # Select first release (typically a wheel or source distribution)
        release = releases[0]
        download_url = release['url']
        
        # Create temporary directory
        temp_dir = Path(tempfile.mkdtemp())
        
        # Download package
        package_path = temp_dir / os.path.basename(download_url)
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status()
            with open(package_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        # Extract package
        import shutil
        import zipfile
        import tarfile
        
        extract_path = temp_dir / package_name
        extract_path.mkdir(exist_ok=True)
        
        if package_path.suffix in ['.whl', '.zip']:
            with zipfile.ZipFile(package_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
        elif package_path.suffix in ['.tar.gz', '.tgz']:
            with tarfile.open(package_path, 'r:gz') as tar_ref:
                tar_ref.extractall(extract_path)
        
        return extract_path
    
    except Exception as e:
        raise RuntimeError(f"Failed to download PyPI package: {str(e)}")


def _download_pypi_package(package_name: str, temp_dir: Path) -> Path:
    """Placeholder for PyPI package download functionality"""
    raise NotImplementedError("Remote package analysis is not yet implemented")
