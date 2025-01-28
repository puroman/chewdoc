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
    responsibilities = []
    
    if module.get("classes"):
        responsibilities.append(f"Defines {len(module['classes'])} core classes")
    if module.get("functions"):
        responsibilities.append(f"Provides {len(module['functions'])} key functions")
    if module.get("constants"):
        responsibilities.append(f"Contains {len(module['constants'])} important constants")
    
    if not responsibilities:
        return "General utility module"
        
    return ". ".join(responsibilities) + "." 