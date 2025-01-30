# Module processing and AST-related utilities
from pathlib import Path
import ast
import fnmatch
import logging
from typing import Dict, List, Optional
from chewdoc.config import ChewdocConfig
from chewdoc.ast_utils import extract_docstrings, extract_type_info

logger = logging.getLogger(__name__)


def process_modules(package_path: Path, config: ChewdocConfig) -> list:
    """Find and process modules in package with init.py handling"""
    modules = []
    
    # Always include __init__.py if present
    init_py = package_path / "__init__.py"
    if init_py.exists():
        modules.append({
            "name": package_path.name,
            "path": str(init_py),
            "imports": [],
            "internal_deps": []
        })

    # Existing module discovery logic
    for py_file in package_path.glob("**/*.py"):
        if _should_process(py_file, config):
            try:
                modules.append(_process_single_file(py_file, package_path))
            except Exception as e:
                logger.warning(f"Skipping {py_file}: {str(e)}")
    
    return [m for m in modules if m is not None]


def _should_process(path: Path, config: ChewdocConfig) -> bool:
    """Check if file should be processed"""
    return (
        path.name != "__init__.py" and  # Handled separately
        not _is_excluded(path, config) and
        path.is_file()
    )


def _create_module_data(
    file_path: Path, package_path: Path, config: ChewdocConfig
) -> dict | None:
    """Create module data with robust error handling."""
    try:
        with open(file_path, "r") as f:
            file_content = f.read()

        # Validate syntax before parsing
        try:
            ast_tree = ast.parse(file_content)
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
            return None

        # Validate module name
        module_name = _get_module_name(file_path, package_path)
        if not module_name:
            logger.warning(f"Could not determine module name for {file_path}")
            return None

        return {
            "name": module_name,
            "path": str(file_path),
            "ast": ast_tree,
            "internal_deps": _find_internal_deps(ast_tree, package_path.name),
            "imports": _find_imports(ast_tree, package_path.name),
        }
    except Exception as e:
        logger.warning(f"Error processing module {file_path}: {e}")
        return None


def _is_excluded(path: Path, config: ChewdocConfig) -> bool:
    """Check if path matches any exclude patterns"""
    # Convert exclude patterns to strings and filter invalid types
    exclude_patterns = [str(p) for p in config.exclude_patterns if isinstance(p, (str, Path))]
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


def _find_constants(node: ast.AST, config: ChewdocConfig) -> Dict[str, Dict]:
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
    def __init__(self, config: ChewdocConfig, examples: Optional[List] = None):
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


def _process_single_file(py_file: Path, package_path: Path) -> dict:
    """Process a single Python file and return module data"""
    module_data = _create_module_data(py_file, package_path, ChewdocConfig())
    return {
        "name": module_data["name"],
        "path": str(py_file),
        "imports": module_data["imports"],
        "internal_deps": module_data["internal_deps"]
    } if module_data else None
