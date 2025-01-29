import click
from pathlib import Path
from chewdoc.metadata import get_package_metadata
from chewdoc.module_processor import process_modules
from chewdoc.package_discovery import find_python_packages
from src.chewdoc.package_analysis import analyze_package
from src.chewdoc.doc_generation import generate_docs
from src.chewdoc.config import ChewdocConfig, load_config
import logging

logger = logging.getLogger(__name__)

@click.command()
@click.argument("source", type=click.Path(exists=True))
@click.option("--output", "-o", required=True, type=click.Path(), help="Output directory")
@click.option("--local/--pypi", default=True, help="Local package or PyPI package")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def cli(source: str, output: str, local: bool, verbose: bool) -> None:
    """Main entry point for package analysis"""
    config = load_config()
    package_info = analyze_package(source, is_local=local, config=config, verbose=verbose)
    generate_docs(package_info, Path(output), verbose=verbose)

def analyze_package(source: str, is_local: bool, config: ChewdocConfig, verbose: bool = False) -> dict:
    """Analyze a Python package structure and contents."""
    try:
        package_path = Path(source)
        if not is_local:
            package_path = _download_pypi_package(source, config.temp_dir)

        packages = find_python_packages(package_path, config)
        if not packages:
            raise ValueError("No valid Python packages found")

        processor = DocProcessor(config)
        modules = []
        for pkg in packages:
            modules += process_modules(Path(pkg["path"]), config)

        return {
            "package": packages[0]["name"],
            "modules": modules,
            "dependencies": analyze_relationships(modules, packages[0]["name"]),
            "metadata": get_package_metadata(source, None, is_local)
        }
    except Exception as e:
        logger.error(f"Package analysis failed: {str(e)}")
        if verbose:
            logger.exception("Analysis error details:")
        raise
