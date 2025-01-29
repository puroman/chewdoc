import click
from pathlib import Path
from chewdoc.metadata import get_package_metadata, _download_pypi_package
from chewdoc.module_processor import process_modules, DocProcessor
from chewdoc.package_discovery import find_python_packages
from src.chewdoc.package_analysis import analyze_package, analyze_relationships
from src.chewdoc.doc_generation import generate_docs
from src.chewdoc.config import ChewdocConfig, load_config
import logging
import ast
import sys
from typing import List, Dict, Any

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
        package_path = Path(source).resolve()
        
        # Validate source path
        if not package_path.exists():
            raise ValueError(f"Source path does not exist: {source}")
        
        # Download PyPI package if needed
        if not is_local:
            package_path = _download_pypi_package(source, config.temp_dir)

        # Find Python packages
        packages = find_python_packages(package_path, config)
        
        # Validate package discovery
        if not packages:
            raise ValueError(f"No valid Python packages found in {source}")

        # Process modules with error handling
        modules = []
        for pkg in packages:
            try:
                pkg_modules = process_modules(Path(pkg["path"]), config)
                modules.extend(pkg_modules)
            except Exception as module_error:
                if verbose:
                    logger.warning(f"Error processing package {pkg['name']}: {module_error}")
        
        # Final validation
        if not modules:
            raise ValueError(f"No valid modules found in package {source}")

        # Prepare package metadata
        primary_package = packages[0]
        return {
            "name": primary_package["name"],
            "package": primary_package["name"],
            "modules": modules,
            "dependencies": analyze_relationships(modules, primary_package["name"]),
            "metadata": get_package_metadata(source, None, is_local)
        }
    except Exception as e:
        logger.error(f"Package analysis failed: {str(e)}")
        if verbose:
            logger.exception("Detailed error:")
        raise RuntimeError(f"Package analysis failed: {str(e)}")

def _find_imports(node: ast.AST, package_root: str) -> List[Dict[str, Any]]:
    imports = []
    stdlib_modules = sys.stdlib_module_names
    
    for node in ast.walk(node):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                full_path = alias.name if isinstance(node, ast.Import) else f"{node.module}.{alias.name}"
                first_part = full_path.split('.')[0]
                import_type = "stdlib" if first_part in stdlib_modules else "external"
                imports.append({"full_path": full_path, "type": import_type})
    return imports
