import ast
from pathlib import Path
from typing import Dict, Any, Optional
import importlib.metadata
import subprocess
import tempfile
import shutil
import tomli
from chewdoc.formatters.myst_writer import generate_myst
import re

def analyze_package(source: str, version: str = None, is_local: bool = False) -> Dict[str, Any]:
    """Analyze a Python package with enhanced error handling"""
    try:
        package_info = get_package_metadata(source, version, is_local)
        package_root = get_package_path(source, is_local)
        
        package_info["modules"] = []
        for module in process_modules(package_root):
            module["docstrings"] = extract_docstrings(module["ast"])
            module["type_info"] = extract_type_info(module["ast"])
            package_info["modules"].append(module)
            
        return package_info
    except Exception as e:
        raise RuntimeError(f"Package analysis failed: {str(e)}") from e

def process_modules(package_path: Path) -> list:
    """Discover and process package modules with type info"""
    modules = []
    for file_path in package_path.rglob("*.py"):
        module_data = {
            "name": _get_module_name(file_path, package_path),
            "path": str(file_path),
            "ast": parse_ast(file_path),
            "imports": [],
            "types": {}
        }
        
        module_data["imports"] = _find_imports(module_data["ast"])
        module_data["types"] = extract_type_info(module_data["ast"])
        modules.append(module_data)
    
    # Second pass to find internal dependencies
    module_names = {m['name'] for m in modules}
    for module in modules:
        module['internal_deps'] = [
            imp for imp in module['imports']
            if any(imp.startswith(p) for p in module_names)
        ]
    
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

def get_local_metadata(pkg_path: Path) -> Dict[str, Any]:
    """Extract metadata from local package"""
    # Try pyproject.toml first
    pyproject = pkg_path / "pyproject.toml"
    if pyproject.exists():
        return parse_pyproject(pyproject)
        
    # Fallback to setup.py
    return {
        "name": pkg_path.name,
        "version": "0.0.0",
        "author": "Unknown",
        "license": "Proprietary",
        "dependencies": [],
        "python_requires": ">=3.6"
    }

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

def parse_pyproject(path: Path) -> Dict[str, Any]:
    """Parse pyproject.toml for package metadata"""
    with open(path, "rb") as f:
        data = tomli.load(f)
    
    project = data.get("project", {})
    return {
        "name": project.get("name", path.parent.name),
        "version": project.get("version", "0.0.0"),
        "author": ", ".join(project.get("authors", [{"name": "Unknown"}])[0]["name"]),
        "license": project.get("license", {}).get("text", "Proprietary"),
        "dependencies": project.get("dependencies", []),
        "python_requires": project.get("requires-python", ">=3.6")
    }

def extract_docstrings(node: ast.AST) -> Dict[str, str]:
    """Extract docstrings from AST nodes with error handling"""
    docstrings = {}
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.Module, ast.ClassDef, ast.FunctionDef)):
            try:
                docstring = ast.get_docstring(child, clean=True)
                if docstring:
                    key = f"{getattr(child, 'name', 'module')}:{child.lineno}"
                    docstrings[key] = docstring
            except Exception as e:
                continue
    return docstrings

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
    """Generate documentation from analyzed package data"""
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
    """Extract imported modules from AST"""
    imports = []
    for child in ast.walk(node):
        if isinstance(child, ast.Import):
            for alias in child.names:
                imports.append(alias.name)
        elif isinstance(child, ast.ImportFrom):
            module = child.module or ""
            imports.append(module)
    return list(set(imports))

def extract_type_info(node: ast.AST) -> Dict[str, Any]:
    """Enhanced type hint parsing with qualified names"""
    type_info = {
        "cross_references": set(),
        "functions": {},
        "classes": {},
        "variables": {}
    }
    
    # Track class definitions
    for child in ast.walk(node):
        if isinstance(child, ast.ClassDef):
            type_info["cross_references"].add(child.name)
    
    def _track_references(annotation: str, context: str = "") -> str:
        """Track references with context awareness"""
        # Match class names and generic types
        pattern = r'\b((\w+\.)*[A-Z]\w*)\b(?:\[.*?\])?'
        for match in re.finditer(pattern, annotation):
            base_type = match.group(1).split("[")[0]  # Handle generics
            if '.' in base_type:
                type_info["cross_references"].add(base_type)
                type_info["cross_references"].add(base_type.split('.')[-1])
            else:
                type_info["cross_references"].add(base_type)
        return annotation
    
    # Update _get_annotation to track references
    def _get_annotation(node: ast.AST) -> str:
        annotation = ast.unparse(node) if node else ""
        return _track_references(annotation)
    
    for child in ast.walk(node):
        # Function arguments and return types
        if isinstance(child, ast.FunctionDef):
            type_info["functions"][child.name] = {
                "args": _get_arg_types(child.args),
                "returns": _get_return_type(child.returns)
            }
        
        # Class methods and attributes
        elif isinstance(child, ast.ClassDef):
            type_info["classes"][child.name] = {
                "methods": {},
                "attributes": _get_class_attributes(child)
            }
        
        # Variable annotations
        elif isinstance(child, ast.AnnAssign):
            if isinstance(child.target, ast.Name):
                type_info["variables"][child.target.id] = _get_annotation(child.annotation)
    
    return type_info

def _get_arg_types(args: ast.arguments) -> Dict[str, str]:
    """Extract argument types from a function definition."""
    arg_types = {}
    for arg in args.args:
        if arg.annotation:
            arg_types[arg.arg] = _get_annotation(arg.annotation)
    return arg_types

def _get_return_type(returns: ast.AST) -> str:
    """Extract return type annotation."""
    return _get_annotation(returns) if returns else "Any"

def _get_class_attributes(cls: ast.ClassDef) -> Dict[str, str]:
    """Extract class attribute type annotations."""
    attributes = {}
    for node in ast.walk(cls):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            attributes[node.target.id] = _get_annotation(node.annotation)
    return attributes

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