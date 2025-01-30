# Package metadata handling
from pathlib import Path
import tempfile
from typing import Dict, Optional, Any
from datetime import datetime
import os
import requests
import logging

logger = logging.getLogger(__name__)


def get_package_metadata(
    source: str, version: Optional[str] = None, is_local: bool = True
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
    logger.info(f"Getting package metadata for {'local' if is_local else 'PyPI'} package: {source}")
    if is_local:
        path = Path(source)
        if not path.exists():
            logger.error(f"Local package path does not exist: {source}")
            raise ValueError(f"Local package path does not exist: {source}")

        metadata = {
            "package": path.name,
            "path": str(path.resolve()),
            "version": version or "0.0.0",
            "python_requires": ">=3.8",
        }
        logger.debug(f"Retrieved local package metadata: {metadata}")
        return metadata
    else:
        logger.info(f"Fetching PyPI package metadata for {source} version {version or 'latest'}")
        package_path = get_pypi_metadata(source, version)
        metadata = {
            "package": source,
            "path": str(package_path),
            "version": version or "latest",
            "python_requires": ">=3.8",
        }
        logger.debug(f"Retrieved PyPI package metadata: {metadata}")
        return metadata


def get_local_metadata(path: Path) -> dict:
    logger.info(f"Getting local metadata for path: {path}")
    metadata = {
        "name": path.name,
        "version": "0.0.0",
        "author": "Unknown",
        "license": "Proprietary",
        "python_requires": ">=3.6",
    }
    logger.debug(f"Retrieved local metadata: {metadata}")
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
    logger.info(f"Downloading PyPI package: {package_name} version {version or 'latest'}")
    try:
        # Fetch package metadata from PyPI
        url = f"https://pypi.org/pypi/{package_name}/json"
        logger.debug(f"Fetching package metadata from: {url}")
        response = requests.get(url)
        response.raise_for_status()

        package_data = response.json()
        logger.debug("Successfully retrieved package metadata from PyPI")

        # Determine version
        if not version:
            version = package_data["info"]["version"]
        logger.info(f"Using package version: {version}")

        # Find appropriate release
        releases = package_data["releases"].get(version, [])
        if not releases:
            logger.error(f"No release found for version {version}")
            raise ValueError(f"No release found for version {version}")

        # Select first release (typically a wheel or source distribution)
        release = releases[0]
        download_url = release["url"]
        logger.debug(f"Selected download URL: {download_url}")

        # Create temporary directory
        temp_dir = Path(tempfile.mkdtemp())
        logger.debug(f"Created temporary directory: {temp_dir}")

        # Download package
        package_path = temp_dir / os.path.basename(download_url)
        logger.info(f"Downloading package to: {package_path}")
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status()
            with open(package_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        logger.debug("Package download completed")

        # Extract package
        import shutil
        import zipfile
        import tarfile

        extract_path = temp_dir / package_name
        extract_path.mkdir(exist_ok=True)
        logger.info(f"Extracting package to: {extract_path}")

        if package_path.suffix in [".whl", ".zip"]:
            logger.debug("Extracting ZIP/wheel file")
            with zipfile.ZipFile(package_path, "r") as zip_ref:
                zip_ref.extractall(extract_path)
        elif package_path.suffix in [".tar.gz", ".tgz"]:
            logger.debug("Extracting tar.gz file")
            with tarfile.open(package_path, "r:gz") as tar_ref:
                tar_ref.extractall(extract_path)

        logger.info("Package extraction completed successfully")
        return extract_path

    except Exception as e:
        logger.error(f"Failed to download PyPI package: {str(e)}")
        raise RuntimeError(f"Failed to download PyPI package: {str(e)}")


def _download_pypi_package(package_name: str, temp_dir: Path) -> Path:
    """Placeholder for PyPI package download functionality"""
    logger.error("Remote package analysis is not yet implemented")
    raise NotImplementedError("Remote package analysis is not yet implemented")
