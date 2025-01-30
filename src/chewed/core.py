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


def analyze_package(
    source: str, 
    is_local: bool = True,
    config: Optional[chewedConfig] = None,
    verbose: bool = False
) -> Dict[str, Any]:
    """Analyze a Python package with improved error handling"""
    config = config or chewedConfig()
    source_path = Path(source).resolve()

    if not source_path.exists():
        raise ValueError(f"Source path does not exist: {source}")

    try:
        packages = find_python_packages(source_path, config)
        if not packages:
            raise ValueError("No valid Python packages found")

        # Process modules with empty package check
        modules = []
        processed_paths = set()  # Track processed package paths
        
        for pkg in packages:
            pkg_path = Path(pkg["path"])
            if str(pkg_path) in processed_paths:
                continue
                
            if not any(pkg_path.glob("*.py")):
                continue
                
            pkg_modules = process_package_modules(pkg_path, config)
            if pkg_modules:
                modules.extend(pkg_modules)
                processed_paths.add(str(pkg_path))

        if not modules:
            raise RuntimeError("No valid modules found")

        return {
            "package": get_package_name(source_path),
            "modules": modules,
            "config": config
        }

    except ValueError as e:
        logger.error(str(e))
        raise
    except Exception as e:
        logger.error(f"Package analysis failed: {str(e)}", exc_info=verbose)
        raise RuntimeError(f"Package analysis failed: {str(e)}") from e
