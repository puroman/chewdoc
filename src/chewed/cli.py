import os
import click
import logging
from pathlib import Path
from typing import Optional
import tempfile

from chewed.core import analyze_package
from chewed.doc_generation import generate_docs
from chewed.metadata import get_pypi_metadata
from chewed.config import chewedConfig, load_config
from chewed._version import __version__

logger = logging.getLogger(__name__)


@click.group()
@click.version_option()
def cli():
    """Documentation generator for Python packages."""
    pass


@cli.command()
@click.argument('source', type=str)
@click.option('--output', '-o', default='docs',
              help='Output directory for documentation')
@click.option('--local/--pypi', default=True,
              help='Process local package or download from PyPI')
@click.option('--verbose', '-v', count=True,
              help='Enable verbose output')
def generate(source: str, output: str, local: bool, verbose: bool):
    """Generate documentation for a Python package."""
    try:
        logger.info("📚 Generating project documentation...")
        logger.info("🕒 Timing documentation generation...")
        
        config = load_config()
        logger.info("Loading configuration")
        
        package_info = analyze_package(source, is_local=local, config=config)
        logger.info("Analyzing package")
        
        generate_docs(package_info, Path(output), verbose=verbose)
        logger.info("Generating documentation")
        
        click.echo(f"✅ Documentation generated in {output}/")
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise click.ClickException(str(e))


def download_package(package_name: str, tmp_dir: Path) -> Path:
    """Download a package from PyPI and return its path."""
    import subprocess
    import tarfile
    import zipfile
    
    download_dir = tmp_dir / "download"
    download_dir.mkdir(exist_ok=True)
    
    try:
        # Download package
        subprocess.run(
            ["pip", "download", "--no-deps", "-d", str(download_dir), package_name],
            check=True,
            capture_output=True,
            text=True
        )
        
        # Find the downloaded package
        packages = list(download_dir.glob(f"{package_name}*"))
        if not packages:
            raise RuntimeError(f"Failed to download package: {package_name}")
        
        # Extract package if it's a compressed file
        package_path = packages[0]
        extracted_dir = tmp_dir / "extracted"
        extracted_dir.mkdir(exist_ok=True)
        
        # Improved extraction logic
        if package_path.suffix in ['.tar.gz', '.tgz']:
            with tarfile.open(package_path, 'r:gz') as tar:
                tar.extractall(path=extracted_dir)
        elif package_path.suffix in ['.zip']:
            with zipfile.ZipFile(package_path, 'r') as zip_ref:
                zip_ref.extractall(extracted_dir)
        elif package_path.suffix in ['.whl']:
            # Handle wheel files
            import zipfile
            with zipfile.ZipFile(package_path, 'r') as wheel:
                wheel.extractall(extracted_dir)
        
        # Find the extracted package directory
        extracted_packages = list(extracted_dir.glob(f"{package_name}*"))
        if not extracted_packages:
            # Try finding any directory
            extracted_packages = [d for d in extracted_dir.iterdir() if d.is_dir()]
        
        if not extracted_packages:
            raise RuntimeError(f"Failed to extract package: {package_name}")
        
        return extracted_packages[0]
        
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to download package: {e.stderr}")


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
