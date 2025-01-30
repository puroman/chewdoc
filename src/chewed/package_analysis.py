# Package analysis core logic
from pathlib import Path
from datetime import datetime
import logging
from typing import Any, Dict, Optional
from .module_processor import process_modules
from .metadata import get_package_metadata
from .relationships import analyze_relationships
from .ast_utils import extract_docstrings, extract_type_info
from .config import chewedConfig
from .utils import find_usage_examples, extract_constant_values, validate_ast
from .package_discovery import (
    find_python_packages,
    get_package_name,
    _is_namespace_package,
)
import ast
import tempfile
import re

logger = logging.getLogger(__name__)


def analyze_package(
    source: str,
    version: Optional[str] = None,
    is_local: bool = True,
    config: Optional[chewedConfig] = None,
    verbose: bool = False,
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

        # Get package name with fallback
        package_name = get_package_name(source_path)
        if not package_name or package_name in ["src", "lib"]:
            # Try to get name from parent directory
            parent_name = source_path.parent.name
            if parent_name and parent_name.isidentifier():
                package_name = parent_name
                logger.info(f"Using parent directory name as package name: {package_name}")
            else:
                # Final fallback: use the last valid directory name in the path
                for part in reversed(source_path.parts):
                    if part and part.isidentifier() and part not in ["src", "lib", "site-packages", "dist-packages"]:
                        package_name = part
                        logger.info(f"Using directory name as package name: {package_name}")
                        break
                else:
                    package_name = "unknown_package"
                    logger.warning("Could not determine package name, using 'unknown_package'")

        if not package_name.isidentifier():
            package_name = "unknown_package"
            logger.warning(f"Invalid package name derived, falling back to 'unknown_package'")

        package_info = {
            "package": package_name,
            "version": version or "unknown",
            "modules": [],
            "relationships": {},
            "metadata": get_package_metadata(source_path),
            "path": str(source_path)
        }

        start = datetime.now()
        module_paths = process_modules(source_path, config)
        
        if not module_paths:
            logger.warning(f"No modules found in {source_path}")
            if config.allow_namespace_packages:
                return package_info
            raise RuntimeError(f"No modules found in {source_path}")
        
        # Enhanced validation with concrete error messages
        validated_modules = []
        for idx, module_data in enumerate(module_paths):
            try:
                if module_data is None:
                    logger.warning(f"Skipping None module at index {idx}")
                    continue
                    
                if not isinstance(module_data, dict):
                    logger.warning(f"Skipping non-dict module at index {idx}: {type(module_data)}")
                    continue

                # Initialize default module structure
                default_module = {
                    "name": "",
                    "path": "",
                    "imports": [],
                    "internal_deps": [],
                }
                
                # Update with actual data
                default_module.update(module_data)
                module_data = default_module
                
                if not module_data["name"]:
                    logger.warning(f"Module at index {idx} missing 'name' key. Full path: {module_data.get('path', 'unknown')}")
                    continue
                    
                module_name = module_data["name"]
                if not module_name.isidentifier():
                    logger.warning(f"Invalid module name '{module_name}' in {module_data.get('path', 'unknown')}")
                    continue
                
                validated_modules.append(module_data)
                
            except Exception as e:
                logger.error(f"❌ Invalid module at index {idx}: {str(e)}")
                if verbose:
                    logger.info(f"Problematic module data: {module_data}", exc_info=True)

        if not validated_modules:
            raise RuntimeError(f"No valid modules found in {source_path}. Check exclude patterns and package structure.")

        try:
            package_info["modules"] = validated_modules
            package_info["relationships"] = analyze_relationships(validated_modules, package_name)
        except Exception as e:
            logger.error(f"Failed to analyze relationships: {str(e)}")
            if verbose:
                logger.info("Module data causing relationship analysis failure:", exc_info=True)
                for idx, module in enumerate(validated_modules):
                    logger.info(f"Module {idx}: {module}")
            package_info["relationships"] = {}

        if verbose:
            duration = datetime.now() - start
            logger.info(f"🏁 Analysis completed in {duration.total_seconds():.3f}s")
            logger.info(f"📊 Processed {len(package_info['modules'])} modules from {source_path}")

        return package_info

    except Exception as e:
        logger.error(f"Package analysis failed for {source_path}: {str(e)}", exc_info=verbose)
        raise


def _derive_package_name(package_path: Path) -> str:
    """Fallback package name derivation from path"""
    try:
        path_parts = package_path.resolve().parts
        for part in reversed(path_parts):
            if part in ("src", "site-packages", "dist-packages"):
                continue
            if "-" in part and part[0].isalpha():
                return re.sub(r"[-_]\d+.*", "", part).replace("_", "-")
            return part.replace("_", "-")
        return "unknown-package"
    except Exception as e:
        logger.warning(f"Package name derivation failed: {str(e)}")
        return "unknown-package"
