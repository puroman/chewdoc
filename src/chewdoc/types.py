from typing import Dict, Any, List
from pathlib import Path

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
        docstring: str = None
    ):
        self.name = name
        self.path = path
        self.imports = imports or []
        self.classes = classes or []
        self.functions = functions or []
        self.docstring = docstring

    def __repr__(self) -> str:
        return f"ModuleInfo(name={self.name}, path={self.path})" 