import click
from pathlib import Path
from chewed.metadata import get_package_metadata, _download_pypi_package
from chewed.module_processor import process_modules, DocProcessor
from chewed.package_discovery import find_python_packages, get_package_name
from chewed.package_analysis import analyze_package, analyze_relationships
from chewed.doc_generation import generate_docs
from chewed.config import chewedConfig, load_config
import logging
import ast
import sys
from typing import List, Dict, Any, Optional
import fnmatch

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


def process_package_modules(pkg_path: Path, config: chewedConfig) -> List[Dict[str, Any]]:
    """Process all Python modules in a package"""
    modules = []
    processed_files = set()  # Track processed files
    
    for py_file in pkg_path.glob("*.py"):
        # Skip already processed files
        if str(py_file.resolve()) in processed_files:
            continue
            
        # Skip excluded files
        if any(fnmatch.fnmatch(str(py_file), pattern) for pattern in config.exclude_patterns):
            continue
            
        # Skip empty __init__.py files
        if py_file.name == "__init__.py" and py_file.stat().st_size == 0:
            continue
            
        try:
            module_info = process_modules([str(py_file)], config)
            if module_info:
                modules.extend(module_info)
                processed_files.add(str(py_file.resolve()))
        except SyntaxError:
            logger.warning(f"Syntax error in {py_file}")
            continue
        except Exception as e:
            logger.warning(f"Failed to process {py_file}: {str(e)}")
            continue
            
    return modules


def analyze_package(source: Path, config: chewedConfig, verbose: bool = False) -> dict:
    """Main package analysis entry point"""
    try:
        # Ensure source is a Path object
        source = Path(source).resolve()
        if not source.exists():
            raise ValueError(f"Package path does not exist: {source}")

        logger.info(f"Analyzing package at: {source}")
        
        # Process modules
        modules = process_modules(source, config)
        if not modules:
            if config.allow_namespace_packages:
                logger.warning(f"Empty namespace package at {source}")
                return _create_empty_package_info(source)
            raise RuntimeError("No valid modules found")

        # Get package name before processing relationships
        package_name = get_package_name(source)
        
        # Analyze relationships with package name
        relationships = analyze_relationships(modules, package_name)
        
        return {
            "package": package_name,  # Use already retrieved name
            "path": str(source),
            "modules": modules,
            "relationships": relationships,
            "metadata": get_package_metadata(source)
        }
        
    except Exception as e:
        logger.error(f"Package analysis failed: {str(e)}")
        raise


def _create_empty_package_info(path: Path) -> dict:
    """Create minimal package info for empty namespace packages"""
    return {
        "package": path.name,
        "path": str(path),
        "modules": [],
        "relationships": {},
        "metadata": {}
    }
