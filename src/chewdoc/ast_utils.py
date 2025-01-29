# AST processing utilities
import ast
from typing import Dict, Any

def extract_docstrings(node: ast.AST) -> Dict[str, str]:
    """Extract docstrings from AST nodes."""
    docs = {}
    for child in ast.walk(node):
        if isinstance(child, (ast.Module, ast.ClassDef, ast.FunctionDef)):
            docstring = ast.get_docstring(child)
            if docstring:
                docs[child.name if hasattr(child, "name") else "module"] = docstring
    return docs

def extract_type_info(node: ast.AST, config: Any) -> Dict[str, Any]:
    """Extract type annotations from AST nodes."""
    type_info = {}
    for child in ast.walk(node):
        if isinstance(child, ast.AnnAssign):
            if isinstance(child.target, ast.Name):
                type_info[child.target.id] = ast.unparse(child.annotation)
        elif isinstance(child, ast.FunctionDef):
            returns = ast.unparse(child.returns) if child.returns else None
            args = [ast.unparse(arg.annotation) for arg in child.args.args if arg.annotation]
            if returns or args:
                type_info[child.name] = {
                    "return_type": returns,
                    "arg_types": args
                }
    return type_info 