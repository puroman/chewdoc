# Module processing and AST-related utilities
from pathlib import Path
import ast
import fnmatch
import logging
from typing import Dict, List, Optional
from .config import ChewdocConfig

logger = logging.getLogger(__name__)

def process_modules(package_path: Path, config: ChewdocConfig) -> list[dict]:
    """Process Python modules in package directory."""
    modules = []
    for file_path in package_path.rglob("*.py"):
        if _is_excluded(file_path, config.exclude_patterns):
            continue
        if module_data := _create_module_data(file_path, package_path, config):
            modules.append(module_data)
    return modules

def _create_module_data(file_path: Path, package_path: Path, config: ChewdocConfig) -> dict | None:
    try:
        with open(file_path, "r") as f:
            ast_tree = ast.parse(f.read())
        return {
            "name": _get_module_name(file_path, package_path),
            "path": str(file_path),
            "ast": ast_tree,
            "internal_deps": _find_internal_deps(ast_tree, package_path.name),
            "imports": _find_imports(ast_tree, package_path.name)
        }
    except SyntaxError as e:
        logger.warning(f"Skipping {file_path} due to syntax error: {e}")
        return None

def _is_excluded(path: Path, exclude_patterns: List[str]) -> bool:
    return any(fnmatch.fnmatch(str(path), pattern) for pattern in exclude_patterns)

def _get_module_name(file_path: Path, package_root: Path) -> str:
    relative_path = file_path.relative_to(package_root)
    return str(relative_path.with_suffix("")).replace("/", ".").replace("src.", "")

def _find_internal_deps(ast_tree: ast.Module, package_name: str) -> List[str]:
    # Implementation of _find_internal_deps function
    pass

def _find_imports(ast_tree: ast.AST, package_name: str) -> List[Dict]:
    """Analyze import statements with dependency classification."""
    imports = []

    class ImportVisitor(ast.NodeVisitor):
        def visit_Import(self, node):
            for alias in node.names:
                self._add_import(alias.name, None)

        def visit_ImportFrom(self, node):
            module = node.module or ""
            for alias in node.names:
                full_path = f"{module}.{alias.name}" if module else alias.name
                self._add_import(full_path, module)

        def _add_import(self, full_path: str, base_module: Optional[str]):
            import_type = "external"
            if full_path.split(".", 1)[0] == package_name:
                import_type = "internal"
            elif base_module and base_module in stdlib_modules:
                import_type = "stdlib"
            
            imports.append({
                "full_path": full_path,
                "name": full_path.split(".")[-1],
                "type": import_type,
                "source": full_path.split(".", 1)[0]
            })

    ImportVisitor().visit(ast_tree)
    return imports

def _find_constants(node: ast.AST, config: ChewdocConfig) -> Dict[str, Dict]:
    """Find and type-annotate module-level constants."""
    constants = {}
    for stmt in node.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    constant_type = "Any"
                    if stmt.annotation:
                        constant_type = ast.unparse(stmt.annotation)
                    constants[target.id] = {
                        "value": ast.unparse(stmt.value),
                        "type": constant_type
                    }
        elif isinstance(stmt, ast.AnnAssign):
            if isinstance(stmt.target, ast.Name) and stmt.target.id.isupper():
                constants[stmt.target.id] = {
                    "value": ast.unparse(stmt.value) if stmt.value else None,
                    "type": ast.unparse(stmt.annotation)
                }
    return constants

class DocProcessor:
    def __init__(self, config: ChewdocConfig):
        self.config = config
        
    def process_module(self, file_path: Path) -> dict:
        """Process a single module file"""
        try:
            with open(file_path, "r") as f:
                ast_tree = ast.parse(f.read())
                
            return {
                "path": str(file_path),
                "ast": ast_tree,
                "docstrings": extract_docstrings(ast_tree),
                "type_info": extract_type_info(ast_tree, self.config)
            }
        except SyntaxError as e:
            logger.error(f"Syntax error in {file_path}: {str(e)}")
            return {} 

# Add stdlib modules list at the bottom of the file
stdlib_modules = {
    "sys", "os", "re", "math", "datetime", "json", 
    "pathlib", "typing", "collections", "itertools"
} 