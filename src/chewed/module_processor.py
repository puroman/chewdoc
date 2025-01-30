# Module processing and AST-related utilities
from pathlib import Path
import ast
import fnmatch
import logging
from typing import Dict, List, Optional
from chewed.config import chewedConfig
from chewed.ast_utils import extract_docstrings, extract_type_info
import os

logger = logging.getLogger(__name__)


def process_modules(package_path: Path, config: chewedConfig) -> list:
    """Find and process Python modules in a package with better filtering"""
    modules = []
    package_path = Path(package_path)

    try:
        # Walk through the directory tree
        for root, _, files in os.walk(package_path):
            root_path = Path(root)
            
            # Skip hidden directories
            if any(part.startswith('.') for part in root_path.parts):
                continue

            # Process Python files
            for file in files:
                if not file.endswith('.py'):
                    continue
                    
                file_path = root_path / file
                
                # Skip files in excluded patterns
                if any(fnmatch.fnmatch(str(file_path), pattern) 
                      for pattern in config.exclude_patterns):
                    continue

                try:
                    # Process the file
                    module = _process_single_file(file_path, package_path, config)
                    if module:
                        modules.append(module)
                except Exception as e:
                    logger.warning(f"Failed to process {file_path}: {str(e)}")
                    continue

        # Handle namespace packages if allowed and no modules found
        if not modules and config.allow_namespace_packages:
            logger.info(f"Processing namespace package at {package_path}")
            modules.append({
                "name": package_path.name,
                "path": str(package_path),
                "imports": [],
                "internal_deps": [],
                "type_info": {"classes": {}, "functions": {}}
            })

    except Exception as e:
        logger.error(f"Error processing modules in {package_path}: {str(e)}")
        raise

    return modules


def _should_process(path: Path, config: chewedConfig) -> bool:
    """Check if file should be processed"""
    return (
        path.name != "__init__.py"  # Handled separately
        and not _is_excluded(path, config)
        and path.is_file()
    )


def _create_module_data(
    file_path: Path, package_path: Path, config: chewedConfig
) -> dict | None:
    """Create module data from a Python file"""
    try:
        # Ensure we're working with Path objects
        file_path = Path(file_path)
        package_path = Path(package_path)
        
        # Get relative path for module name
        try:
            rel_path = file_path.relative_to(package_path)
            module_name = ".".join(part for part in rel_path.parent.parts + (rel_path.stem,) if part != ".")
        except ValueError:
            logger.error(f"File {file_path} is not under package path {package_path}")
            return None

        # Read and parse the file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {str(e)}")
            return None

        # Extract imports and dependencies
        imports = []
        internal_deps = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
                    if not node.module.startswith('.'):
                        # Check if it's an internal dependency
                        if node.module.startswith(package_path.name):
                            internal_deps.append(node.module)

        return {
            "name": module_name,
            "path": str(file_path),
            "imports": imports,
            "internal_deps": internal_deps,
        }
        
    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
        return None


def _is_excluded(path: Path, config: chewedConfig) -> bool:
    """Check if path matches any exclude patterns"""
    # Convert exclude patterns to strings and filter invalid types
    exclude_patterns = [
        str(p) for p in config.exclude_patterns if isinstance(p, (str, Path))
    ]
    str_path = str(path.resolve())

    return any(
        fnmatch.fnmatch(str_path, pattern)
        for pattern in exclude_patterns
        if isinstance(pattern, str)
    )


def _get_module_name(file_path: Path, package_root: Path) -> str:
    relative_path = file_path.relative_to(package_root)
    return str(relative_path.with_suffix("")).replace("/", ".").replace("src.", "")


def _find_internal_deps(ast_tree: ast.Module, package_name: str) -> List[str]:
    """Find internal dependencies within the package."""
    internal_deps = []

    class InternalDependencyVisitor(ast.NodeVisitor):
        def visit_Import(self, node):
            for alias in node.names:
                if alias.name.startswith(package_name):
                    internal_deps.append(alias.name)

        def visit_ImportFrom(self, node):
            if node.module and node.module.startswith(package_name):
                internal_deps.append(node.module)

    visitor = InternalDependencyVisitor()
    visitor.visit(ast_tree)

    return list(set(internal_deps))


def _find_imports(ast_tree: ast.AST, package_name: str) -> List[Dict]:
    """Analyze import statements with robust dependency classification."""
    imports = []
    stdlib_modules = {
        "sys",
        "os",
        "re",
        "math",
        "datetime",
        "json",
        "pathlib",
        "typing",
        "collections",
        "itertools",
    }

    class ImportVisitor(ast.NodeVisitor):
        def visit_Import(self, node):
            for alias in node.names:
                self._add_import(alias.name, None)

        def visit_ImportFrom(self, node):
            base_module = node.module or ""
            for alias in node.names:
                full_path = f"{base_module}.{alias.name}" if base_module else alias.name
                self._add_import(full_path, base_module.split(".")[0])

        def _add_import(self, full_path: str, root_module: Optional[str]):
            import_type = "external"
            first_part = full_path.split(".")[0]

            # Classify import type
            if first_part == package_name or full_path.startswith(f"{package_name}."):
                import_type = "internal"
            elif first_part in stdlib_modules:
                import_type = "stdlib"

            imports.append(
                {
                    "full_path": full_path,
                    "name": full_path.split(".")[-1],
                    "type": import_type,
                    "source": first_part,
                }
            )

    ImportVisitor().visit(ast_tree)
    return imports


def _find_constants(node: ast.AST, config: chewedConfig) -> Dict[str, Dict]:
    """Find and type-annotate module-level constants."""
    constants = {}
    for stmt in node.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and (
                    target.id.isupper() or target.id == "__version__"
                ):
                    value = ast.unparse(stmt.value).strip()
                    const_type = "Any"
                    if hasattr(stmt, "type_comment") and stmt.type_comment:
                        const_type = stmt.type_comment
                    else:
                        # Infer type from value
                        if value.isdigit():
                            const_type = "int"
                        elif value.startswith(("'", '"')):
                            const_type = "str"
                    constants[target.id] = {"value": value, "type": const_type}
        elif isinstance(stmt, ast.AnnAssign):
            if isinstance(stmt.target, ast.Name) and stmt.target.id.isupper():
                constants[stmt.target.id] = {
                    "value": ast.unparse(stmt.value) if stmt.value else None,
                    "type": ast.unparse(stmt.annotation),
                }
    return constants


class DocProcessor:
    def __init__(self, config: chewedConfig, examples: Optional[List] = None):
        self.config = config
        self.examples = self._validate_examples(examples or [])

    def _validate_examples(self, raw_examples: List) -> List[Dict]:
        valid = []
        # Handle single string example
        if isinstance(raw_examples, str):
            return [{"code": raw_examples, "output": None}]

        for ex in raw_examples:
            if isinstance(ex, str):
                valid.append({"code": ex, "output": None})
            elif isinstance(ex, dict):
                if "content" in ex:  # Legacy format
                    valid.append({"code": ex["content"], "output": ex.get("result")})
                elif "code" in ex:
                    valid.append({"code": str(ex["code"]), "output": ex.get("output")})
        return valid

    def process_module(self, file_path: Path) -> dict:
        """Process a single module file"""
        try:
            with open(file_path, "r") as f:
                ast_tree = ast.parse(f.read())

            return {
                "path": str(file_path),
                "ast": ast_tree,
                "docstrings": extract_docstrings(ast_tree),
                "type_info": extract_type_info(ast_tree, self.config),
            }
        except SyntaxError as e:
            logger.error(f"Syntax error in {file_path}: {str(e)}")
            return {}


# Add stdlib modules list at the bottom of the file
stdlib_modules = {
    "sys",
    "os",
    "re",
    "math",
    "datetime",
    "json",
    "pathlib",
    "typing",
    "collections",
    "itertools",
}


def _process_single_file(
    py_file: Path, package_path: Path, config: chewedConfig
) -> dict | None:
    """Process a single Python file and return module data"""
    try:
        py_file = Path(py_file)
        package_path = Path(package_path)
        
        if not py_file.is_file():
            logger.warning(f"Not a file: {py_file}")
            return None
            
        module_data = _create_module_data(py_file, package_path, config)
        if module_data:
            return {
                "name": module_data["name"],
                "path": str(py_file),
                "imports": module_data["imports"],
                "internal_deps": module_data["internal_deps"],
            }
        return None
        
    except Exception as e:
        logger.error(f"Failed to process {py_file}: {str(e)}")
        return None
