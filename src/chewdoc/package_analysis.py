# Package analysis core logic
from pathlib import Path
from datetime import datetime
import logging
from typing import Any, Dict
from .module_processor import process_modules
from .metadata import get_package_metadata
from .relationships import analyze_relationships
from .ast_utils import extract_docstrings, extract_type_info
from .config import ChewdocConfig
from .utils import find_usage_examples, extract_constant_values, validate_ast
from .package_discovery import find_python_packages, get_package_name, _is_namespace_package

logger = logging.getLogger(__name__)

def analyze_package(
    source: str,
    is_local: bool = True,
    version: str | None = None,
    config: ChewdocConfig | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Analyze Python package and extract documentation metadata."""
    path = Path(source).resolve() if is_local else Path(tempfile.gettempdir()) / f"pypi_{source}"
    if not is_local:
        path.mkdir(exist_ok=True)
    
    if verbose and (start := datetime.now()):
        logger.info(f"🚀 Starting analysis at {start:%H:%M:%S.%f}"[:-3])

    config = config or ChewdocConfig()
    try:
        if verbose:
            logger.info("🔍 Fetching package metadata...")
        package_info = get_package_metadata(source, version, is_local)
        package_info.setdefault("python_requires", ">=3.6")
        package_info.setdefault("license", "Proprietary")
        package_path = path if is_local else get_package_path(path, is_local)
        package_name = package_info["package"]

        if verbose:
            logger.info(f"📦 Processing package: {package_name}")
            logger.info("🧠 Processing module ASTs...")

        package_info["modules"] = []
        module_paths = process_modules(path, config)

        if not module_paths:
            raise ValueError("No valid modules found in package")

        for module_data in module_paths:
            module_path = Path(module_data["path"])
            if verbose:
                logger.info(f"🔄 Processing: {module_data['name']}")

            with open(module_path, "r") as f:
                module_ast = ast.parse(f.read())

            validate_ast(module_ast)
            module_info = {
                "name": module_data["name"],
                "path": str(module_path),
                "ast": module_ast,
                "docstrings": extract_docstrings(module_ast),
                "type_info": extract_type_info(module_ast, config),
                "constants": {
                    name: {"value": value}
                    for name, value in extract_constant_values(module_ast)
                    if name.isupper()
                },
                "examples": find_usage_examples(module_ast),
                "imports": module_data["imports"],
                "internal_deps": module_data.get("internal_deps", []),
            }
            package_info["modules"].append(module_info)

        package_info["relationships"] = analyze_relationships(package_info["modules"], package_name)

        if verbose:
            duration = datetime.now() - start
            logger.info(f"🏁 Analysis completed in {duration.total_seconds():.3f}s")
            logger.info(f"📊 Processed {len(package_info['modules'])} modules")

        return package_info
    except SyntaxError as e:
        raise ValueError(f"Syntax error in {path}: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Package analysis failed: {str(e)}") from e 