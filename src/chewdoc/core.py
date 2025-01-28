import ast
from pathlib import Path
from typing import Dict, Any, Optional
import importlib.metadata
import subprocess
import tempfile
import shutil
try:
    import tomli
except ImportError:
    import tomllib as tomli  # Python 3.11+
from chewdoc.formatters.myst_writer import generate_myst
import re
from chewdoc.constants import KNOWN_TYPES, EXCLUDE_PATTERNS
import fnmatch

def analyze_package(source: str, version: str = None, is_local: bool = False) -> Dict[str, Any]:
    """Analyze a Python package and extract documentation information.
    
    Args:
        source: Package name (PyPI) or path (local)
        version: Optional version for PyPI packages
        is_local: Whether source is a local path
        
    Returns:
        Dict containing package metadata, modules, and documentation
        
    Raises:
        RuntimeError: If package analysis fails
        ValueError: If PyPI package not found
        FileNotFoundError: If local package path invalid
    """
    try:
        package_info = get_package_metadata(source, version, is_local)
        package_root = get_package_path(source, is_local)
        
        package_info["modules"] = []
        for module in process_modules(package_root):
            module.update({
                "docstrings": extract_docstrings(module["ast"]),
                "type_info": extract_type_info(module["ast"]),
                "imports": _find_imports(module["ast"]),
                "constants": _find_constants(module["ast"]),
                "examples": _find_usage_examples(module["ast"])
            })
            package_info["modules"].append(module)
            
        return package_info
    except Exception as e:
        raise RuntimeError(f"Package analysis failed: {str(e)}") from e

def process_modules(package_path: Path) -> list:
    """Process Python modules in a package directory.
    
    Recursively discovers and analyzes Python modules in the package,
    excluding files matching EXCLUDE_PATTERNS.
    
    Args:
        package_path: Root directory of the package
        
    Returns:
        List of module data dictionaries containing:
        - name: Full module name
        - path: Module file path
        - ast: Parsed AST
        - internal_deps: List of internal dependencies
    """
    modules = []
    for file_path in package_path.rglob("*.py"):
        # Skip files matching exclusion patterns
        if any(fnmatch.fnmatch(part, pattern)
               for part in file_path.parts
               for pattern in EXCLUDE_PATTERNS):
            continue
            
        module_data = {
            "name": _get_module_name(file_path, package_path),
            "path": str(file_path),
            "ast": parse_ast(file_path),
            "internal_deps": []
        }
        
        # Only track internal dependencies
        all_imports = _find_imports(module_data["ast"])
        module_names = {m['name'] for m in modules}
        module_data["internal_deps"] = [
            imp['full_path'] for imp in all_imports
            if imp['full_path'] in module_names
        ]
        
        modules.append(module_data)
    
    return modules

def parse_ast(file_path: Path) -> ast.AST:
    """Parse Python file to AST"""
    with open(file_path, "r") as f:
        return ast.parse(f.read())

def get_package_metadata(source: str, version: Optional[str], is_local: bool) -> Dict[str, Any]:
    """Extract package metadata from local or PyPI package"""
    if is_local:
        return get_local_metadata(Path(source))
    return get_pypi_metadata(source, version)

def get_local_metadata(path: Path) -> dict:
    """Extract package metadata from pyproject.toml or setup.py."""
    try:
        return parse_pyproject(path / "pyproject.toml")
    except FileNotFoundError:
        setup_py = path / "setup.py"
        if setup_py.exists():
            with open(setup_py) as f:
                content = f.read()
                name_match = re.search(r"name=['\"](.+?)['\"]", content)
                version_match = re.search(r"version=['\"](.+?)['\"]", content)
                return {
                    "name": name_match.group(1) if name_match else path.name,
                    "version": version_match.group(1) if version_match else "0.0.0"
                }
    return {"name": path.name, "version": "0.0.0"}

def get_pypi_metadata(name: str, version: Optional[str]) -> Dict[str, Any]:
    """Retrieve PyPI package metadata"""
    try:
        dist = importlib.metadata.distribution(name)
    except importlib.metadata.PackageNotFoundError:
        raise ValueError(f"Package {name} not found in PyPI")
    
    return {
        "name": dist.metadata["Name"],
        "version": dist.version,
        "author": dist.metadata["Author"],
        "license": dist.metadata["License"],
        "dependencies": [str(req) for req in dist.requires] if dist.requires else [],
        "python_requires": dist.metadata["Requires-Python"] or ">=3.6"
    }

def get_package_path(source: str, is_local: bool) -> Path:
    """Get root path for package sources"""
    if is_local:
        path = Path(source).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Package path not found: {source}")
        return path
        
    try:
        dist = importlib.metadata.distribution(source)
        return Path(dist.locate_file(""))
    except importlib.metadata.PackageNotFoundError:
        raise ValueError(f"Package {source} not installed")

def parse_pyproject(path: Path) -> dict:
    """Parse pyproject.toml for package metadata"""
    with open(path, "rb") as f:
        data = tomli.load(f)
    
    # Check for poetry projects
    project = data.get("project") or data.get("tool", {}).get("poetry", {})
    return {
        "name": project.get("name", path.parent.name),
        "version": project.get("version", "0.0.0"),
        "author": (project.get("authors", [{}])[0].get("name", "Unknown")),
        "license": project.get("license", {}).get("text", "Proprietary"),
        "dependencies": project.get("dependencies", []),
        "python_requires": project.get("requires-python", ">=3.6")
    }

def extract_docstrings(node: ast.AST) -> Dict[str, str]:
    """Enhanced docstring extraction with context tracking"""
    docs = {}
    for child in ast.walk(node):
        if isinstance(child, (ast.Module, ast.ClassDef, ast.FunctionDef)):
            try:
                docstring = ast.get_docstring(child, clean=True)
                if docstring:
                    key = f"{type(child).__name__}:{getattr(child, 'name', 'module')}"
                    docs[key] = {
                        "doc": docstring,
                        "line": child.lineno,
                        "context": _get_code_context(child)
                    }
            except Exception as e:
                continue
    return docs

def _get_code_context(node: ast.AST) -> str:
    """Get surrounding code context for documentation"""
    if isinstance(node, ast.ClassDef):
        bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
        return f"class {node.name}({', '.join(bases)})"
    elif isinstance(node, ast.FunctionDef):
        return f"def {node.name}{_format_function_signature(node.args, node.returns)}"
    return ""

def download_pypi_package(name: str, version: str = None) -> Path:
    """Download PyPI package to temporary directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = ["pip", "download", "--no-deps", "--dest", tmpdir]
        if version:
            cmd.append(f"{name}=={version}")
        else:
            cmd.append(name)
            
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to download package: {result.stderr}")
            
        downloaded = list(Path(tmpdir).glob("*.tar.gz")) + list(Path(tmpdir).glob("*.whl"))
        if not downloaded:
            raise FileNotFoundError("No package files downloaded")
            
        # Extract package
        extract_dir = Path(tmpdir) / "extracted"
        shutil.unpack_archive(str(downloaded[0]), str(extract_dir))
        return extract_dir / downloaded[0].stem.split("-")[0]

def generate_docs(package_info: Dict[str, Any], output_path: str) -> None:
    """Generate MyST documentation from package analysis data.
    
    Creates a documentation directory structure with:
    - Module documentation files
    - API reference
    - Cross-references
    - Usage examples
    
    Args:
        package_info: Package analysis data from analyze_package()
        output_path: Directory to write documentation files
        
    Example:
        ```python
        info = analyze_package("mypackage", is_local=True)
        generate_docs(info, "docs/mypackage")
        ```
    """
    generate_myst(package_info, Path(output_path))

def _get_module_name(file_path: Path, package_root: Path) -> str:
    """Get full module name from file path (internal)"""
    rel_path = file_path.relative_to(package_root)
    
    if rel_path.name == "__init__.py":
        if rel_path.parent == Path("."):  # Handle root package
            return package_root.name
        return f"{package_root.name}." + ".".join(rel_path.parent.parts)
    return f"{package_root.name}." + ".".join(rel_path.with_suffix("").parts)

def _find_imports(node: ast.AST) -> list:
    """Collect imports with their source and type context"""
    imports = []
    seen = set()
    
    for n in ast.walk(node):
        if isinstance(n, ast.Import):
            for alias in n.names:
                key = (alias.name, None, 'module')
                if key not in seen:
                    seen.add(key)
                    imports.append({
                        'name': alias.name.split('.')[0],
                        'full_path': alias.name,
                        'source': None,
                        'type': 'module'
                    })
        elif isinstance(n, ast.ImportFrom):
            module = n.module or ''
            for alias in n.names:
                key = (alias.name, module, 'object')
                if key not in seen:
                    seen.add(key)
                    imports.append({
                        'name': alias.name,
                        'full_path': f"{module}.{alias.name}" if module else alias.name,
                        'source': module,
                        'type': 'object'
                    })
    return imports

def extract_type_info(node: ast.AST) -> Dict[str, Any]:
    """Extract type hints and relationships from AST.
    
    Analyzes Python code to collect:
    - Class hierarchies and methods
    - Function signatures
    - Variable type annotations
    - Cross-references between types
    
    Args:
        node: AST node to analyze (usually module)
        
    Returns:
        Dictionary containing:
        - cross_references: Set of referenced type names
        - functions: Dict of function signatures
        - classes: Dict of class information
        - variables: Dict of typed variables
    """
    type_info = {
        "cross_references": set(),
        "functions": {},
        "classes": {},
        "variables": {}
    }
    
    # Track current class context using stack instead of parent references
    class_stack = []
    
    class TypeVisitor(ast.NodeVisitor):
        """AST visitor for extracting type information from Python code.
        
        This visitor traverses the AST to collect:
        - Class definitions and their methods
        - Function signatures and return types
        - Variable type annotations
        
        The collected information is stored in the type_info dictionary
        passed to extract_type_info().
        """
        
        def visit_ClassDef(self, node):
            """Process class definition and collect method information."""
            # Generate fully qualified class name
            if class_stack:
                full_name = f"{class_stack[-1]}.{node.name}"
            else:
                full_name = node.name
                
            type_info["cross_references"].add(full_name)
            type_info["classes"][full_name] = {
                "attributes": {},
                "methods": {}
            }
            
            # Push current class to stack and process children
            class_stack.append(full_name)
            self.generic_visit(node)
            class_stack.pop()
            
        def visit_FunctionDef(self, node):
            # Capture method relationships
            if class_stack:
                class_name = class_stack[-1]
                type_info["classes"][class_name]["methods"][node.name] = {
                    "args": _get_args(node.args),
                    "returns": _get_return_type(node.returns)
                }
            self.generic_visit(node)
            
        def visit_AnnAssign(self, node):
            # Handle variable type annotations
            if isinstance(node.target, ast.Name):
                var_name = node.target.id
                type_info["variables"][var_name] = _get_annotation(node.annotation)
    
    TypeVisitor().visit(node)
    return type_info

def _get_args(args: ast.arguments) -> Dict[str, str]:
    """Extract argument types from a function definition."""
    arg_types = {}
    for arg in args.args:
        if arg.annotation:
            arg_types[arg.arg] = _get_annotation(arg.annotation)
    return arg_types

def _get_return_type(returns: ast.AST) -> str:
    """Extract return type annotation."""
    return _get_annotation(returns) if returns else "Any"

def _get_annotation(node: ast.AST) -> str:
    """Extract type annotation from an AST node."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Constant):
        return str(node.value)
    elif isinstance(node, ast.Subscript):
        value = _get_annotation(node.value)
        slice_val = _get_annotation(node.slice)
        return f"{value}[{slice_val}]"
    elif isinstance(node, ast.Attribute):
        value = _get_annotation(node.value)
        return f"{value}.{node.attr}"
    elif isinstance(node, ast.BinOp):
        left = _get_annotation(node.left)
        right = _get_annotation(node.right)
        return f"{left} | {right}"  # Handle Union types
    else:
        return str(node)

def _get_package_name(path: Path) -> str:
    """Extract package name from filename"""
    match = re.search(r"([a-zA-Z0-9_\-]+)-\d+\.\d+\.\d+", path.name)
    return match.group(1) if match else path.stem

def find_python_packages(path: Path) -> dict:
    """Discover Python packages in a directory tree.
    
    Recursively searches for Python packages (directories with __init__.py)
    while respecting exclusion patterns.
    
    Args:
        path: Root directory to search
        
    Returns:
        Dict mapping package names to:
        - path: Package directory
        - modules: Nested package dict
        
    Example:
        ```python
        packages = find_python_packages(Path("src"))
        for name, info in packages.items():
            print(f"Found package {name} at {info['path']}")
        ```
    """
    packages = {}
    
    for entry in path.iterdir():
        # Check against all exclusion patterns
        if any(fnmatch.fnmatch(part, pattern) 
               for part in entry.parts 
               for pattern in EXCLUDE_PATTERNS):
            continue
            
        if entry.is_dir():
            # Add package discovery logic here
            if (entry / "__init__.py").exists():
                pkg_name = entry.name
                packages[pkg_name] = {
                    "path": entry,
                    "modules": find_python_packages(entry)  # Recursive discovery
                }
            else:
                # Handle non-package directories
                packages.update(find_python_packages(entry))
                
    return packages 

def _find_constants(node: ast.AST) -> Dict[str, Any]:
    """Find module-level constants with type hints"""
    constants = {}
    for n in ast.walk(node):
        if isinstance(n, ast.Assign):
            for target in n.targets:
                if isinstance(target, ast.Name):
                    constants[target.id] = {
                        "value": ast.unparse(n.value),
                        "type": _get_annotation(n.annotation) if getattr(n, 'annotation', None) else None,
                        "line": n.lineno
                    }
        elif isinstance(n, ast.AnnAssign):
            if isinstance(n.target, ast.Name):
                constants[n.target.id] = {
                    "value": ast.unparse(n.value) if n.value else None,
                    "type": _get_annotation(n.annotation),
                    "line": n.lineno
                }
    return constants

def _find_usage_examples(node: ast.AST) -> list:
    """Extract usage examples from docstrings and tests"""
    examples = []
    for n in ast.walk(node):
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant):
            if "Example:" in (docstring := n.value.value):
                examples.append({
                    "type": "doctest",
                    "content": "\n".join(line.strip() for line in docstring.split("\n")),
                    "line": n.lineno
                })
        elif isinstance(n, ast.FunctionDef) and n.name.startswith("test_"):
            examples.append({
                "type": "pytest",
                "name": n.name,
                "line": n.lineno,
                "body": ast.unparse(n)
            })
    return examples 