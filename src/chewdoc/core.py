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
from chewdoc.formatters.myst_writer import _format_function_signature, generate_myst
import re
from chewdoc.constants import CLI_HELP
import fnmatch
from chewdoc.config import ChewdocConfig, load_config


def analyze_package(
    source: str,
    is_local: bool = True,
    version: Optional[str] = None,
    config: Optional[ChewdocConfig] = None,
) -> Dict[str, Any]:
    """Analyze a Python package and extract documentation information.

    Args:
        source: Package name (PyPI) or path (local)
        version: Optional version for PyPI packages
        is_local: Whether source is a local path
        config: Optional configuration object

    Returns:
        Dict containing package metadata, modules, and documentation

    Raises:
        RuntimeError: If package analysis fails
        ValueError: If PyPI package not found
        FileNotFoundError: If local package path invalid
    """
    config = config or load_config()
    try:
        package_info = get_package_metadata(source, version, is_local)
        package_root = get_package_path(source, is_local)

        package_info["modules"] = []
        for module in process_modules(package_root, config):
            module.update(
                {
                    "docstrings": extract_docstrings(module["ast"]),
                    "type_info": extract_type_info(module["ast"], config),
                    "imports": _find_imports(module["ast"]),
                    "constants": _find_constants(module["ast"], config),
                    "examples": _find_usage_examples(module["ast"]),
                }
            )
            package_info["modules"].append(module)

        return package_info
    except Exception as e:
        raise RuntimeError(f"Package analysis failed: {str(e)}") from e


def process_modules(package_path: Path, config: ChewdocConfig) -> list:
    """Process Python modules in a package directory.

    Recursively discovers and analyzes Python modules in the package,
    excluding files matching EXCLUDE_PATTERNS.

    Args:
        package_path: Root directory of the package
        config: Configuration object

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
        if any(
            fnmatch.fnmatch(part, pattern)
            for part in file_path.parts
            for pattern in config.exclude_patterns
        ):
            continue

        module_data = {
            "name": _get_module_name(file_path, package_path),
            "path": str(file_path),
            "ast": parse_ast(file_path),
            "internal_deps": [],
        }

        # Only track internal dependencies
        all_imports = _find_imports(module_data["ast"])
        module_names = {m["name"] for m in modules}
        module_data["internal_deps"] = [
            imp["full_path"] for imp in all_imports if imp["full_path"] in module_names
        ]

        modules.append(module_data)

    return modules


def parse_ast(file_path: Path) -> ast.AST:
    """Parse Python file to AST"""
    with open(file_path, "r") as f:
        return ast.parse(f.read())


def get_package_metadata(
    source: str, version: Optional[str], is_local: bool
) -> Dict[str, Any]:
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
                    "version": version_match.group(1) if version_match else "0.0.0",
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
        "python_requires": dist.metadata["Requires-Python"] or ">=3.6",
    }


def get_package_path(source: str, is_local: bool) -> Path:
    """Get package path from source string"""
    if is_local:
        # Ensure source is converted to Path object
        return Path(source).resolve()
    else:
        # Handle PyPI package paths
        return Path(importlib.metadata.distribution(source).location)


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
        "python_requires": project.get("requires-python", ">=3.6"),
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
                        "context": _get_code_context(child),
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

        downloaded = list(Path(tmpdir).glob("*.tar.gz")) + list(
            Path(tmpdir).glob("*.whl")
        )
        if not downloaded:
            raise FileNotFoundError("No package files downloaded")

        # Extract package
        extract_dir = Path(tmpdir) / "extracted"
        shutil.unpack_archive(str(downloaded[0]), str(extract_dir))
        return extract_dir / downloaded[0].stem.split("-")[0]


def generate_docs(
    package_info: Dict[str, Any],
    output_path: Path,
    config: Optional[ChewdocConfig] = None,
) -> None:
    """Generate MyST documentation from package analysis data.

    Creates a documentation directory structure with:
    - Module documentation files
    - API reference
    - Cross-references
    - Usage examples

    Args:
        package_info: Package analysis data from analyze_package()
        output_path: Directory to write documentation files
        config: Optional configuration object

    Example:
        ```python
        info = analyze_package("mypackage", is_local=True)
        generate_docs(info, "docs/mypackage")
        ```
    """
    config = config or load_config()
    generate_myst(
        package_info,
        output_path,
        template_dir=config.template_dir,
        enable_cross_refs=config.enable_cross_references,
    )


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
    for n in ast.walk(node):
        if isinstance(n, ast.Import):
            for alias in n.names:
                imports.append({
                    "name": alias.name,
                    "source": None,
                    "full_path": alias.name,
                    "type": "module"
                })
        elif isinstance(n, ast.ImportFrom):
            module = n.module.split('.') if n.module else []
            for alias in n.names:
                full_path = f"{'.'.join(module)}.{alias.name}" if module else alias.name
                imports.append({
                    "name": alias.name,
                    "source": n.module,
                    "full_path": full_path,
                    "type": "module"
                })
    return imports


def extract_type_info(node: ast.AST, config: ChewdocConfig) -> Dict[str, Any]:
    """Extract type hints and relationships from AST.

    Analyzes Python code to collect:
    - Class hierarchies and methods
    - Function signatures
    - Variable type annotations
    - Cross-references between types

    Args:
        node: AST node to analyze (usually module)
        config: Configuration object

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
        "variables": {},
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
            type_info["classes"][full_name] = {"attributes": {}, "methods": {}}

            # Push current class to stack and process children
            class_stack.append(full_name)
            self.generic_visit(node)
            class_stack.pop()

        def visit_FunctionDef(self, node):
            """Process function definition and collect type information."""
            func_name = node.name
            type_info["functions"][func_name] = {
                "args": _get_arg_types(node.args, config),
                "returns": _get_return_type(node.returns, config)
            }
            self.generic_visit(node)

        def visit_AnnAssign(self, node):
            """Process annotated assignments."""
            if isinstance(node.target, ast.Name):
                type_info["variables"][node.target.id] = _get_annotation(
                    node.annotation, config
                )
            self.generic_visit(node)

    TypeVisitor().visit(node)
    return type_info


def _get_arg_types(args: ast.arguments, config: ChewdocConfig) -> Dict[str, str]:
    """Extract argument types from a function definition."""
    arg_types = {}
    # Handle cases with just ... in args
    if not getattr(args, "args", None):
        return arg_types
    for arg in args.args:
        if arg.annotation:
            arg_types[arg.arg] = _get_annotation(arg.annotation, config)
    return arg_types


def _get_return_type(returns: ast.AST, config: ChewdocConfig) -> str:
    """Extract return type annotation."""
    return _get_annotation(returns, config) if returns else "Any"


def _get_annotation(node: ast.AST, config: ChewdocConfig) -> str:
    """Extract type annotation from an AST node."""
    if isinstance(node, ast.Name):
        return config.known_types.get(node.id, node.id)
    elif isinstance(node, ast.Constant):
        return str(node.value)
    elif isinstance(node, ast.Subscript):
        value = _get_annotation(node.value, config)
        # Handle Ellipsis in subscript slices
        if isinstance(node.slice, ast.Ellipsis):
            return f"{value}[...]"
        slice_val = _get_annotation(node.slice, config)
        return f"{value}[{slice_val}]"
    elif isinstance(node, ast.Attribute):
        value = _get_annotation(node.value, config)
        return f"{value}.{node.attr}"
    elif isinstance(node, ast.BinOp):
        left = _get_annotation(node.left, config)
        right = _get_annotation(node.right, config)
        return f"{left} | {right}"
    elif isinstance(node, ast.Ellipsis):
        return "..."
    else:
        return str(node)


def _get_package_name(path: Path) -> str:
    """Extract package name from filename"""
    match = re.search(r"([a-zA-Z0-9_\-]+)-\d+\.\d+\.\d+", path.name)
    return match.group(1) if match else path.stem


def find_python_packages(
    path: Path, config: Optional[ChewdocConfig] = None
) -> Dict[str, Dict]:
    """Discover Python packages with configurable exclusion patterns"""
    config = config or load_config()
    packages = {}

    for entry in path.iterdir():
        if any(
            fnmatch.fnmatch(entry.name, pattern) for pattern in config.exclude_patterns
        ):
            continue

        if entry.is_dir():
            # Add package discovery logic here
            if (entry / "__init__.py").exists():
                pkg_name = entry.name
                packages[pkg_name] = {
                    "path": entry,
                    "modules": find_python_packages(entry),  # Recursive discovery
                }
            else:
                # Handle non-package directories
                packages.update(find_python_packages(entry))

    return packages


def _find_constants(node: ast.AST, config: ChewdocConfig) -> Dict[str, Any]:
    """Find module-level constants with type hints"""
    constants = {}
    for n in ast.walk(node):
        if isinstance(n, ast.Assign):
            for target in n.targets:
                if isinstance(target, ast.Name):
                    constants[target.id] = {
                        "value": ast.unparse(n.value),
                        "type": (
                            _get_annotation(n.annotation, config)
                            if getattr(n, "annotation", None)
                            else None
                        ),
                        "line": n.lineno,
                    }
        elif isinstance(n, ast.AnnAssign):
            if isinstance(n.target, ast.Name):
                constants[n.target.id] = {
                    "value": ast.unparse(n.value) if n.value else None,
                    "type": _get_annotation(n.annotation, config),
                    "line": n.lineno,
                }
    return constants


def _find_usage_examples(node: ast.AST) -> list:
    """Extract usage examples from docstrings and tests"""
    examples = []
    for n in ast.walk(node):
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant):
            if isinstance(n.value.value, str) and "Example:" in (docstring := n.value.value):
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
