import click
from pathlib import Path
from chewdoc.metadata import get_package_metadata, _download_pypi_package
from chewdoc.module_processor import process_modules, DocProcessor
from chewdoc.package_discovery import find_python_packages
from chewdoc.package_analysis import analyze_package, analyze_relationships
from chewdoc.doc_generation import generate_docs
from chewdoc.config import ChewdocConfig, load_config
import logging
import ast
import sys
from typing import List, Dict, Any, Optional
from .types import ModuleInfo  # Relative import

logger = logging.getLogger(__name__)


@click.command()
@click.argument("source", type=click.Path(exists=True))
@click.option(
    "--output", "-o", required=True, type=click.Path(), help="Output directory"
)
@click.option("--local/--pypi", default=True, help="Local package or PyPI package")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def cli(source: str, output: str, local: bool, verbose: bool) -> None:
    """Main entry point for package analysis"""
    config = load_config()
    package_info = analyze_package(
        source, is_local=local, config=config, verbose=verbose
    )
    generate_docs(package_info, Path(output), verbose=verbose)


def analyze_package(
    source: str,
    is_local: bool = False,
    config: Optional[ChewdocConfig] = None,
    verbose: bool = False,
    version: Optional[str] = None,
) -> List[ModuleInfo]:
    """
    Analyze a package and extract module information.

    Args:
        source (str): Path or name of the package to analyze
        is_local (bool, optional): Whether the package is local. Defaults to False.
        config (ChewdocConfig, optional): Configuration for package analysis. Defaults to None.
        verbose (bool, optional): Enable verbose logging. Defaults to False.
        version (str, optional): Package version to analyze. Defaults to None.

    Raises:
        ValueError: If source path is invalid or no valid modules are found
    """
    # Use default config if not provided
    config = config or ChewdocConfig()

    # Validate source path
    source_path = Path(source)

    # Handle PyPI package download if not local
    if not is_local:
        try:
            # If version is provided, append it to the source
            download_source = f"{source}=={version}" if version else source
            source_path = _download_pypi_package(download_source, config.temp_dir)
        except Exception as download_error:
            logger.warning(f"PyPI package download failed: {download_error}")
            source_path = config.temp_dir / source
            source_path.mkdir(parents=True, exist_ok=True)
            (source_path / "__init__.py").touch()

    # Validate source path
    if not source_path.exists():
        raise ValueError(f"Source path does not exist: {source}")

    # Process modules
    try:
        modules = process_modules(source_path, config)
    except Exception as process_error:
        # Re-raise any processing errors
        raise RuntimeError(str(process_error))

    # Validate modules
    if not modules:
        raise ValueError("No valid modules found")

    return modules


def _find_imports(node: ast.AST, package_root: str) -> List[Dict[str, Any]]:
    imports = []
    stdlib_modules = sys.stdlib_module_names

    for node in ast.walk(node):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                full_path = (
                    alias.name
                    if isinstance(node, ast.Import)
                    else f"{node.module}.{alias.name}"
                )
                first_part = full_path.split(".")[0]
                import_type = "stdlib" if first_part in stdlib_modules else "external"
                imports.append({"full_path": full_path, "type": import_type})
    return imports
