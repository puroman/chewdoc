from pathlib import Path
import logging
from typing import Any, Dict, List, Union
from .formatters.myst_writer import MystWriter
from .types import ModuleInfo

logger = logging.getLogger(__name__)


def generate_docs(
    package_info: Union[Dict[str, Any], List[ModuleInfo]],
    output_path: Path,
    verbose: bool = False,
) -> None:
    """
    Generate documentation for a package.

    Args:
        package_info (Union[Dict[str, Any], List[ModuleInfo]]): Package information
        output_path (Path): Directory to generate documentation in
        verbose (bool, optional): Enable verbose logging. Defaults to False.
    """
    # Ensure output directory exists
    output_path.mkdir(parents=True, exist_ok=True)

    # Normalize package_info to a dictionary if it's a list of modules
    if isinstance(package_info, list):
        package_info = {
            "package": "unknown",  # Default package name
            "modules": package_info,
        }

    # Validate package_info
    if not isinstance(package_info, dict):
        raise ValueError("Invalid package information format")

    # Prepare modules
    modules = package_info.get("modules", [])
    package_name = package_info.get("package", "unknown")

    # Create index file
    index_path = output_path / "index.md"
    with open(index_path, "w") as f:
        f.write(f"# {package_name} Documentation\n\n")

    # Process each module
    for module in modules:
        # Determine module name and path
        module_name = module.get("name", "unknown")
        module_path = output_path / f"{module_name}.md"

        # Write module documentation
        with open(module_path, "w") as f:
            f.write(f"# Module: {module_name}\n\n")

    if verbose:
        logger.info(f"Generated documentation for {len(modules)} modules")
