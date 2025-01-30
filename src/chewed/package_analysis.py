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
    start = datetime.now()

    if not source_path.exists():
        raise ValueError(f"Source path does not exist: {source}")

    try:
        packages = find_python_packages(source_path, config)
        if not packages:
            raise RuntimeError("No valid modules found")

        # Get package name with fallback
        package_name = get_package_name(source_path)
        if not package_name or package_name in ["src", "lib"]:
            package_name = _derive_package_name(source_path)

        package_info = {
            "package": package_name,
            "path": str(source_path),
            "modules": [],
            "relationships": {},
            "metadata": get_package_metadata(source_path)
        }

        try:
            modules = process_modules(source_path, config)
            if not modules:
                raise RuntimeError("No valid modules found")
            
            validated_modules = []
            for idx, module_data in enumerate(modules):
                if not isinstance(module_data, dict):
                    logger.warning(f"Invalid module data at index {idx}")
                    continue
                    
                if not module_data.get("name"):
                    logger.warning(f"Module missing name at index {idx}")
                    continue
                    
                validated_modules.append(module_data)

            if not validated_modules:
                raise RuntimeError("No valid modules found")

            package_info["modules"] = validated_modules
            package_info["relationships"] = analyze_relationships(validated_modules, package_name)

        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Failed to process modules: {str(e)}")
            raise RuntimeError("No valid modules found")

        if verbose:
            duration = datetime.now() - start
            logger.info(f"🏁 Analysis completed in {duration.total_seconds():.3f}s")
            logger.info(f"📊 Processed {len(package_info['modules'])} modules from {source_path}")

        return package_info

    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"Package analysis failed for {source_path}: {str(e)}", exc_info=verbose)
        raise RuntimeError("No valid modules found")


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
