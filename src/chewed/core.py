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
from typing import List, Dict, Any

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


def analyze_package(
    source: str, is_local: bool, config: chewedConfig, verbose: bool = False
) -> dict:
    """Main analysis entry point with proper error handling"""
    try:
        package_path = Path(source)

        # Validate source path exists
        if not package_path.exists():
            raise ValueError(f"Source path does not exist: {source}")

        packages = find_python_packages(package_path, config)
        if not packages:
            # Use namespace package fallback if configured
            if config.namespace_fallback:
                packages = [{"name": package_path.name, "path": str(package_path)}]
            else:
                raise RuntimeError(f"No valid Python packages found in {source}")

        # Process modules for each package
        all_modules = []
        for pkg in packages:
            try:
                modules = process_modules(Path(pkg["path"]), config)

                # If no modules found, create a minimal module for namespace packages
                if not modules and config.namespace_fallback:
                    modules = [
                        {
                            "name": pkg["name"],
                            "path": pkg["path"],
                            "imports": [],
                            "internal_deps": [],
                        }
                    ]

                if not modules:
                    raise RuntimeError(
                        f"Package {pkg['name']} contains no valid modules"
                    )

                all_modules.extend(modules)
            except Exception as module_error:
                if not config.namespace_fallback:
                    raise

        return {
            "package": get_package_name(package_path),
            "modules": all_modules,
            "metadata": get_package_metadata(
                source=str(package_path.resolve()),
                is_local=is_local,
                version=getattr(config, "version", "0.0.0"),
            ),
            "config": config.model_dump(),
        }
    except ValueError as ve:
        # Specific handling for path not existing
        raise ValueError(str(ve))
    except Exception as e:
        logger.error(f"Package analysis failed: {str(e)}")
        raise RuntimeError(f"Package analysis failed: {str(e)}") from e
