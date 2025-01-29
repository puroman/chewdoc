import ast
from chewdoc.config import ChewdocConfig
from typing import Any, List, Tuple, Union
from pathlib import Path


def get_annotation(node: ast.AST, config: ChewdocConfig) -> str:
    """Extract type annotation from an AST node (moved from core.py)"""
    if isinstance(node, ast.Name):
        return config.known_types.get(node.id, node.id)
    elif isinstance(node, ast.Constant):
        return str(node.value)
    elif isinstance(node, ast.Subscript):
        value = get_annotation(node.value, config)
        if isinstance(node.slice, ast.Ellipsis):
            return f"{value}[...]"
        slice_val = get_annotation(node.slice, config)
        return f"{value}[{slice_val}]"
    elif isinstance(node, ast.Attribute):
        value = get_annotation(node.value, config)
        return f"{value}.{node.attr}"
    elif isinstance(node, ast.BinOp):
        left = get_annotation(node.left, config)
        right = get_annotation(node.right, config)
        return f"{left} | {right}"
    elif isinstance(node, ast.Ellipsis):
        return "..."
    else:
        return str(node)


def infer_responsibilities(module: dict) -> str:
    """Generate module responsibility description based on contents"""
    def safe_get_names(items, key="name") -> list:
        """Safely extract names from mixed list/dict structures"""
        if isinstance(items, dict):
            return [v.get(key, "") for v in items.values() if v.get(key)]
        if isinstance(items, list):
            return [item.get(key, "") for item in items if item.get(key)]
        return []

    responsibilities = []
    
    # Handle classes
    if classes := module.get("classes"):
        class_names = safe_get_names(classes)
        class_list = class_names[:3]
        resp = "Defines core classes: " + ", ".join(class_list)
        if len(class_names) > 3:
            resp += f" (+{len(class_names)-3} more)"
        responsibilities.append(resp)
    
    # Handle functions
    if functions := module.get("functions"):
        func_names = safe_get_names(functions)
        func_list = func_names[:3]
        resp = "Provides key functions: " + ", ".join(func_list)
        if len(func_names) > 3:
            resp += f" (+{len(func_names)-3} more)"
        responsibilities.append(resp)
    
    # Handle constants
    if constants := module.get("constants"):
        const_names = safe_get_names(constants)
        const_list = const_names[:3]
        resp = "Contains constants: " + ", ".join(const_list)
        if len(const_names) > 3:
            resp += f" (+{len(const_names)-3} more)"
        responsibilities.append(resp)
    
    if not responsibilities:
        return "General utility module with mixed responsibilities"
        
    return "\n- ".join([""] + responsibilities)


def validate_ast(node: ast.AST, module_path: Path) -> None:
    """Validate AST structure for documentation processing"""
    if not isinstance(node, ast.AST):
        raise TypeError(f"Expected AST node, got {type(node).__name__}")
    if not hasattr(node, 'body'):
        raise ValueError("Invalid AST structure - missing body attribute")
    
    # Allow __init__.py files with only pass statements
    is_init_file = module_path.name == "__init__.py"
    if is_init_file:
        if all(isinstance(stmt, ast.Pass) for stmt in node.body):
            return
        if not node.body:
            return
    
    # Check for minimum required elements
    has_elements = any(
        isinstance(stmt, (ast.FunctionDef, ast.ClassDef, ast.Assign)) 
        for stmt in node.body
    )
    if not has_elements:
        # Allow modules with only docstrings
        has_docstring = any(
            isinstance(stmt, ast.Expr) and isinstance(stmt.value, (ast.Str, ast.Constant))
            for stmt in node.body
        )
        if not has_docstring:
            raise ValueError("Empty or invalid module AST structure")

    # Check for common serialization artifacts
    if any(isinstance(stmt, dict) for stmt in getattr(node, 'body', [])):
        raise ValueError("AST contains serialized dictionaries instead of nodes")

    if hasattr(node, 'body') and any(isinstance(stmt, (str, dict)) for stmt in node.body):
        raise ValueError("AST contains invalid node types")


def find_usage_examples(node: ast.AST) -> list:
    """Placeholder example finder (implement your logic here)"""
    return []  # TODO: Add actual example extraction logic


def format_function_signature(args: ast.arguments, returns: ast.AST, config: ChewdocConfig) -> str:
    """Format function signature with type annotations"""
    params = []
    for arg in args.args:
        name = arg.arg
        annotation = get_annotation(arg.annotation, config) if arg.annotation else ""
        # Only show annotation if available
        param = f"{name}{': ' + annotation if annotation else ''}"
        params.append(param)
        
    return_type = get_annotation(returns, config) if returns else ""
    return f"({', '.join(params)})" + (f" -> {return_type}" if return_type else "")


def _find_imports(node: ast.AST) -> list:
    """Extract import statements from AST"""
    imports = []
    
    class ImportVisitor(ast.NodeVisitor):
        def visit_Import(self, node):
            for alias in node.names:
                imports.append(alias.name)
                
        def visit_ImportFrom(self, node):
            module = node.module or ""
            for alias in node.names:
                imports.append(f"{module}.{alias.name}" if module else alias.name)
    
    ImportVisitor().visit(node)
    return imports


def extract_constant_values(node: ast.AST) -> List[Tuple[str, str]]:
    """Extract module-level constants with ALL_CAPS names"""
    constants = []
    for stmt in node.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    value = ast.unparse(stmt.value).strip()
                    constants.append((target.id, value))
    return constants


def safe_write(path: Path, content: str, mode: str = "w", overwrite: bool = False) -> None:
    """Atomic file write with directory creation"""
    if path.exists() and not overwrite:
        raise FileExistsError(f"File already exists: {path}")
        
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, mode) as f:
        f.write(content)
