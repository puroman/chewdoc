from typing import Dict, Any, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ModuleInfo:
    """
    Represents information about a Python module.

    Attributes:
        name (str): The name of the module
        path (Path): The file path of the module
        imports (List[Dict[str, Any]]): List of imports in the module
        classes (List[Dict[str, Any]]): List of classes in the module
        functions (List[Dict[str, Any]]): List of functions in the module
        docstring (str, optional): Module-level docstring
    """

    def __init__(
        self,
        name: str,
        path: Path,
        imports: List[Dict[str, Any]] = None,
        classes: List[Dict[str, Any]] = None,
        functions: List[Dict[str, Any]] = None,
        docstring: str = None,
    ):
        logger.debug(f"Initializing ModuleInfo for {name} at {path}")
        self.name = name
        self.path = path
        self.imports = imports or []
        self.classes = classes or []
        self.functions = functions or []
        self.docstring = docstring
        logger.debug(
            f"ModuleInfo initialized with {len(self.imports)} imports, "
            f"{len(self.classes)} classes, {len(self.functions)} functions"
        )

    def __repr__(self) -> str:
        logger.debug(f"Generating repr for ModuleInfo {self.name}")
        return f"ModuleInfo(name={self.name}, path={self.path})"
