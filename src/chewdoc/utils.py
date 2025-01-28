import ast
from chewdoc.config import ChewdocConfig


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
            return [v.get(key, "") for v in items.values()]
        if isinstance(items, list):
            return [item.get(key, "") for item in items]
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
