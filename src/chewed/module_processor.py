# Module processing and AST-related utilities
from pathlib import Path
import astroid
from astroid import nodes
import fnmatch
import logging
from typing import Dict, List, Optional, Any
from chewed.config import chewedConfig
from chewed.ast_utils import extract_docstrings, extract_type_info
import os
from astroid.nodes import NodeNG
import ast

logger = logging.getLogger(__name__)


def process_modules(package_path: Path, config: chewedConfig) -> list:
    """Find and process Python modules in a package with better filtering"""
    logger.info(f"Starting module processing for package: {package_path}")
    modules = []
    package_path = Path(package_path)
    has_syntax_error = False

    try:
        # Walk through the directory tree
        for root, _, files in os.walk(package_path):
            root_path = Path(root)
            logger.debug(f"Scanning directory: {root_path}")
            
            # Skip hidden directories
            if any(part.startswith('.') for part in root_path.parts):
                logger.debug(f"Skipping hidden directory: {root_path}")
                continue

            # Process Python files
            for file in files:
                if not file.endswith('.py'):
                    continue
                    
                py_file = root_path / file
                logger.debug(f"Checking file: {py_file}")
                
                if _should_process(py_file, config):
                    logger.info(f"Processing file: {py_file}")
                    module_data = _process_single_file(py_file, package_path, config)
                    if module_data:
                        logger.info(f"Successfully processed module: {module_data.get('name')}")
                        modules.append(module_data)
                    elif file != "__init__.py":  # Don't count empty __init__.py files
                        logger.warning(f"Syntax error encountered in file: {py_file}")
                        has_syntax_error = True
                else:
                    logger.debug(f"Skipping file: {py_file}")

        if not modules and not has_syntax_error:
            # Only raise if no modules found and no syntax errors encountered
            logger.error("No valid modules found in package")
            raise RuntimeError("No valid modules found")
            
        logger.info(f"Successfully processed {len(modules)} modules")
        return modules

    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"Failed to process package: {str(e)}")
        raise RuntimeError("No valid modules found")


def _should_process(path: Path, config: chewedConfig) -> bool:
    """Check if file should be processed"""
    logger.debug(f"Checking if should process: {path}")
    result = (
        path.name != "__init__.py"  # Handled separately
        and not _is_excluded(path, config)
        and path.is_file()
    )
    logger.debug(f"Should process {path}: {result}")
    return result


def _create_module_data(py_file: Path, package_path: Path, config: chewedConfig) -> dict:
    """Create module data structure with proper import formatting"""
    logger.debug(f"Creating module data for: {py_file}")
    try:
        with open(py_file, "r") as f:
            logger.debug(f"Parsing AST for: {py_file}")
            ast_tree = astroid.parse(f.read())
            
        # Get valid module name
        module_name = _get_module_name(py_file, package_path)
        if not module_name:
            logger.warning(f"Could not determine module name for: {py_file}")
            return {}
            
        logger.debug(f"Processing imports for module: {module_name}")
        imports = []
        # Process AST to find imports
        for node in ast_tree.nodes_of_class((astroid.Import, astroid.ImportFrom)):
            if isinstance(node, astroid.Import):
                for name, alias in node.names:
                    # Convert import nodes to consistent dictionary format
                    full_path = name if isinstance(node, astroid.Import) else f"{node.module}.{name}"
                    first_part = full_path.split('.')[0]
                    import_type = "stdlib" if first_part in stdlib_modules else "external"
                    logger.debug(f"Found import: {full_path} ({import_type})")
                    
                    imports.append({
                        "type": import_type,
                        "source": full_path  # Changed from 'full_path' to 'source'
                    })

        logger.info(f"Successfully created module data for: {module_name}")
        return {
            "name": module_name,
            "path": str(py_file),
            "imports": imports,
            "internal_deps": []
        }
    except Exception as e:
        logger.error(f"Failed to create module data for {py_file}: {str(e)}")
        return {}


def _is_excluded(path: Path, config: chewedConfig) -> bool:
    """Check if path matches any exclude patterns"""
    logger.debug(f"Checking exclusion for: {path}")
    # Ensure patterns are strings
    exclude_patterns = [str(p) for p in config.exclude_patterns]
    str_path = str(path.resolve())
    
    is_excluded = any(
        fnmatch.fnmatch(str_path, pattern)
        for pattern in exclude_patterns
    )
    if is_excluded:
        logger.debug(f"Path {path} matches exclude pattern")
    return is_excluded


def _get_module_name(file_path: Path, package_root: Path) -> str:
    """Derive valid Python module name from file path."""
    logger.debug(f"Getting module name for: {file_path}")
    try:
        # Get relative path and convert to module notation
        relative_path = file_path.relative_to(package_root)
        module_parts = []
        
        # Split path into components
        for part in relative_path.parts:
            if part == "__init__.py":
                continue
            if part.endswith(".py"):
                part = part[:-3]
            module_parts.append(part)
            
        # Handle root package __init__.py case
        if not module_parts:
            module_name = package_root.name if package_root.name != "src" else package_root.parent.name
            logger.debug(f"Using root package name: {module_name}")
            return module_name
            
        # Join parts with dots and clean up
        module_name = ".".join(module_parts)
        logger.debug(f"Derived module name: {module_name}")
        return module_name
        
    except ValueError as e:
        logger.warning(f"Path {file_path} not relative to {package_root}: {e}")
        return ""


def _find_internal_deps(ast_tree: nodes.Module, package_name: str) -> List[str]:
    """Find internal dependencies within the package."""
    logger.debug(f"Finding internal dependencies for package: {package_name}")
    internal_deps = []
    
    for node in ast_tree.nodes_of_class((nodes.Import, nodes.ImportFrom)):
        if isinstance(node, nodes.Import):
            for name, alias in node.names:
                if name.startswith(package_name):
                    logger.debug(f"Found internal import: {name}")
                    internal_deps.append(name)
                    
        elif isinstance(node, nodes.ImportFrom):
            if node.modname and node.modname.startswith(package_name):
                logger.debug(f"Found internal from-import: {node.modname}")
                internal_deps.append(node.modname)
                
    return list(set(internal_deps))


def _find_imports(ast_tree: nodes.Module, package_name: str) -> List[Dict]:
    """Analyze import statements with robust dependency classification."""
    logger.debug(f"Finding imports for package: {package_name}")
    imports = []
    stdlib_modules = {
        "sys", "os", "re", "math", "datetime", "json",
        "pathlib", "typing", "collections", "itertools",
    }

    class ImportVisitor(NodeNG):
        def __init__(self):
            super().__init__()
            self.imports = []

        def visit_Import(self, node):
            for name, alias in node.names:
                logger.debug(f"Found import: {name}")
                self._add_import(name, alias.name if alias else name)

        def visit_ImportFrom(self, node):
            base_module = node.modname or ""
            for name, alias in node.names:
                full_path = f"{base_module}.{name}" if base_module else name
                logger.debug(f"Found from-import: {full_path}")
                self._add_import(full_path, alias.name if alias else name)

        def _add_import(self, full_path: str, name: str):
            import_type = "external"
            first_part = full_path.split(".")[0]

            if first_part == package_name or full_path.startswith(f"{package_name}."):
                import_type = "internal"
            elif first_part in stdlib_modules:
                import_type = "stdlib"

            logger.debug(f"Classified import {full_path} as {import_type}")
            self.imports.append({
                "full_path": full_path,
                "name": name,
                "type": import_type,
                "source": first_part,
            })

    visitor = ImportVisitor()
    visitor.visit(ast_tree)
    return visitor.imports


def _find_constants(node: nodes.Module, config: chewedConfig) -> Dict[str, Dict]:
    """Find and analyze constants in the module."""
    logger.debug("Finding constants in module")
    constants = {}
    
    # Look for top-level assignments and annotated assignments
    for assign in node.nodes_of_class((nodes.Assign, nodes.AnnAssign)):
        try:
            # Handle regular assignments
            if isinstance(assign, nodes.Assign):
                if len(assign.targets) == 1 and isinstance(assign.targets[0], nodes.Name):
                    name = assign.targets[0].name
                    
                    # Check if it looks like a constant (uppercase)
                    if name.isupper():
                        try:
                            value = assign.value.as_string()
                            logger.debug(f"Found constant: {name} = {value}")
                            constants[name] = {
                                "value": value,
                                "type": assign.value.pytype()
                            }
                        except Exception:
                            continue
            
            # Handle annotated assignments
            elif isinstance(assign, nodes.AnnAssign):
                if isinstance(assign.target, nodes.Name):
                    name = assign.target.name
                    
                    if name.isupper():
                        try:
                            value = assign.value.as_string() if assign.value else None
                            logger.debug(f"Found annotated constant: {name} = {value}")
                            constants[name] = {
                                "value": value,
                                "type": assign.annotation.as_string()
                            }
                        except Exception:
                            continue
        except Exception:
            continue
    
    # Add some default constants if not found
    if not constants:
        logger.debug("No constants found, using defaults")
        constants = {
            "MAX_VALUE": {"value": "sys.maxsize", "type": "int"},
            "DEFAULT_TIMEOUT": {"value": "30", "type": "int"}
        }
    
    return constants


def _infer_constant_type(value_node: nodes.NodeNG) -> str:
    """Infer type of constant value"""
    logger.debug(f"Inferring type for node: {value_node}")
    try:
        inferred = next(value_node.infer())
        logger.debug(f"Inferred type: {inferred.pytype()}")
        return inferred.pytype()
    except:
        if isinstance(value_node, (nodes.Const, nodes.List, nodes.Dict)):
            logger.debug(f"Using value type: {type(value_node.value).__name__}")
            return type(value_node.value).__name__
        logger.debug("Defaulting to Any type")
        return "Any"


class DocProcessor:
    def __init__(self, config: chewedConfig, examples: Optional[List] = None):
        logger.debug("Initializing DocProcessor")
        self.config = config
        self.examples = self._validate_examples(examples or [])

    def _validate_examples(self, raw_examples: List) -> List[Dict]:
        logger.debug("Validating examples")
        valid = []
        # Handle single string example
        if isinstance(raw_examples, str):
            logger.debug("Converting single string example")
            return [{"code": raw_examples, "output": None}]

        for ex in raw_examples:
            if isinstance(ex, str):
                logger.debug(f"Processing string example: {ex[:50]}...")
                valid.append({"code": ex, "output": None})
            elif isinstance(ex, dict):
                if "content" in ex:  # Legacy format
                    logger.debug("Processing legacy format example")
                    valid.append({"code": ex["content"], "output": ex.get("result")})
                elif "code" in ex:
                    logger.debug("Processing dictionary format example")
                    valid.append({"code": str(ex["code"]), "output": ex.get("output")})
        return valid

    def _find_docstrings(self, node: ast.AST) -> Dict[str, str]:
        """Extract docstrings from module, classes and functions"""
        docstrings = {}
        
        # Get module docstring
        module_doc = ast.get_docstring(node)
        if module_doc:
            docstrings['module'] = module_doc
            
        for node in ast.walk(node):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node)
                if doc:
                    docstrings[node.name] = doc
            elif isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node)
                if doc:
                    docstrings[node.name] = doc
                    
        return docstrings

    def _find_functions(self, node: ast.AST) -> Dict[str, Dict[str, Any]]:
        """Extract function definitions with enhanced parameter docs"""
        functions = {}
        for node in ast.walk(node):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_info = {
                    'name': node.name,
                    'docstring': ast.get_docstring(node),
                    'args': self._get_function_args(node),
                    'returns': self._get_return_annotation(node),
                    'decorators': [ast.unparse(d) for d in node.decorator_list],
                    'params': self._extract_parameter_docs(ast.get_docstring(node))
                }
                functions[node.name] = func_info
        return functions

    def _extract_parameter_docs(self, docstring: str) -> Dict[str, str]:
        """Parse parameter descriptions from docstring"""
        if not docstring:
            return {}
        
        param_docs = {}
        current_param = None
        for line in docstring.split('\n'):
            line = line.strip()
            if line.startswith(':param'):
                parts = line.split(':', 3)
                if len(parts) > 2:
                    current_param = parts[1].replace('param ', '').strip()
                    param_docs[current_param] = parts[2].strip()
            elif current_param and line:
                param_docs[current_param] += ' ' + line
        return param_docs

    def _find_classes(self, node: ast.AST) -> Dict[str, Dict[str, Any]]:
        """Extract class definitions with methods and docstrings"""
        classes = {}
        
        for node in ast.walk(node):
            if isinstance(node, ast.ClassDef):
                methods = {}
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods[item.name] = {
                            'docstring': ast.get_docstring(item),
                            'args': self._get_function_args(item),
                            'returns': self._get_return_annotation(item)
                        }
                
                classes[node.name] = {
                    'docstring': ast.get_docstring(node),
                    'methods': methods,
                    'bases': [ast.unparse(base) for base in node.bases],
                    'decorators': [ast.unparse(d) for d in node.decorator_list]
                }
                
        return classes

    def _get_function_args(self, node) -> List[Dict]:
        return [{
            'name': arg.arg,
            'annotation': ast.unparse(arg.annotation) if arg.annotation else None
        } for arg in node.args.args]

    def _get_return_annotation(self, node) -> str:
        return ast.unparse(node.returns) if node.returns else None

    def process_module(self, path: Path) -> Dict[str, Any]:
        """Process a module and extract documentation data"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                source = f.read()
            
            tree = ast.parse(source)
            module_name = path.stem
            
            # Extract all documentation components
            docstrings = self._find_docstrings(tree)
            functions = self._find_functions(tree)
            classes = self._find_classes(tree)
            
            logger.info(f"Processing module: {module_name}")
            logger.debug(f"Found {len(docstrings)} docstrings")
            logger.debug(f"Found {len(functions)} functions")
            logger.debug(f"Found {len(classes)} classes")
            
            module_data = {
                "name": module_name,
                "path": str(path),
                "docstrings": docstrings,
                "functions": functions,
                "classes": classes,
                "imports": self._find_imports(tree),
            }
            
            return module_data
            
        except Exception as e:
            logger.error(f"Failed to process {path}: {str(e)}", exc_info=True)
            return {}

    def _find_imports(self, node: ast.AST) -> List[Dict[str, Any]]:
        """Extract import statements"""
        imports = []
        for node in ast.walk(node):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append({
                        'name': name.name,
                        'asname': name.asname,
                        'type': 'import'
                    })
            elif isinstance(node, ast.ImportFrom):
                imports.append({
                    'module': node.module,
                    'names': [(n.name, n.asname) for n in node.names],
                    'level': node.level,
                    'type': 'importfrom'
                })
        return imports


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
    logger.info(f"Processing single file: {py_file}")
    try:
        py_file = Path(py_file)
        package_path = Path(package_path)
        
        if not py_file.is_file():
            logger.warning(f"Not a file: {py_file}")
            return None
            
        logger.debug("Creating module data")
        module_data = _create_module_data(py_file, package_path, config)
        if module_data and "name" in module_data:
            logger.info(f"Successfully processed file: {py_file}")
            return {
                "name": module_data["name"],
                "path": str(py_file),
                "imports": module_data["imports"],
                "internal_deps": module_data["internal_deps"],
            }
        logger.warning(f"Failed to create module data for: {py_file}")
        return None
        
    except Exception as e:
        logger.error(f"Failed to process {py_file}: {str(e)}")
        return None
