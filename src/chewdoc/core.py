import ast
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import importlib.metadata
import subprocess
import tempfile
import shutil
from collections import defaultdict
from datetime import datetime
import click

try:
    import tomli
except ImportError:
    import tomllib as tomli  # Python 3.11+
from src.chewdoc.formatters.myst_writer import MystWriter
from chewdoc.utils import get_annotation, infer_responsibilities, validate_ast, find_usage_examples, format_function_signature, extract_constant_values
import re
from chewdoc.constants import AST_NODE_TYPES
import fnmatch
from chewdoc.config import ChewdocConfig, load_config


def analyze_package(
    source: str,
    is_local: bool = True,
    version: Optional[str] = None,
    config: Optional[ChewdocConfig] = None,
    verbose: bool = False
) -> Dict[str, Any]:
    """Analyze Python package and extract documentation metadata.
    
    Example:
        >>> from chewdoc.core import analyze_package
        >>> result = analyze_package("requests", is_local=False)
        >>> "requests" in result["package"]
        True
    """
    start_time = datetime.now()
    if verbose:
        click.echo(f"🚀 Starting analysis at {start_time:%H:%M:%S.%f}"[:-3])
        click.echo(f"📦 Package source: {source}")

    config = config or ChewdocConfig()
    try:
        if verbose:
            click.echo("🔍 Fetching package metadata...")
        package_info = get_package_metadata(source, version, is_local)
        package_info.setdefault("python_requires", ">=3.6")
        package_info.setdefault("license", "Proprietary")
        package_info.setdefault("imports", defaultdict(list))
        package_path = get_package_path(Path(source), is_local)
        package_name = _get_package_name(package_path)
        package_info["package"] = package_name

        if verbose:
            click.echo(f"📦 Processing package: {package_name}")
            click.echo(f"📂 Found {len(package_info.get('modules', []))} modules")
            click.echo("🧠 Processing module ASTs...")

        package_info["modules"] = []
        processed = 0
        module_paths = process_modules(package_path, config)
        total_modules = len(module_paths)
        
        for module_data in module_paths:
            processed += 1
            module_name = module_data["name"]
            module_path = Path(module_data["path"])
            
            if module_path.name == "__init__.py" and module_path.stat().st_size == 0:
                if verbose:
                    click.echo(f"⏭️  Skipping empty __init__.py: {module_path}")
                continue
            
            if verbose:
                click.echo(f"🔄 Processing ({processed}/{total_modules}): {module_name}")
            
            with open(module_path, "r") as f:
                try:
                    module_ast = ast.parse(f.read())
                except SyntaxError as e:
                    raise ValueError(f"Syntax error in {module_path}: {e}")
            
            validate_ast(module_ast, module_path)
            
            module_info = {
                "name": module_name,
                "path": str(module_path),
                "ast": module_ast,
                "docstrings": extract_docstrings(module_ast),
                "types": extract_type_info(module_ast, config),
                "constants": {
                    name: {"value": value}
                    for name, value in extract_constant_values(module_ast)
                    if name.isupper()
                },
                "examples": find_usage_examples(module_ast),
                "imports": _find_imports(module_ast, package_name),
                "internal_deps": module_data.get("internal_deps", [])
            }
            
            for imp in module_info["imports"]:
                package_info["imports"][imp["full_path"]].append(module_name)
            
            internal_imports = [
                imp["full_path"] for imp in module_info["imports"]
                if imp["type"] == "internal"
            ]
            module_info["internal_deps"] = list(set(internal_imports))
            
            package_info["modules"].append(module_info)

        relationships = _analyze_relationships(package_info["modules"], package_name)
        package_info["relationships"] = relationships

        if verbose:
            duration = datetime.now() - start_time
            click.echo(f"🏁 Analysis completed in {duration.total_seconds():.3f}s")
            click.echo(f"📊 Processed {len(package_info['modules'])} modules")

        return package_info
    except Exception as e:
        raise RuntimeError(f"Package analysis failed: {str(e)}") from e


def process_modules(package_path: Path, config: ChewdocConfig) -> list:
    """Process Python modules in package directory.
    
    Example test case:
    ```python
    def test_module_processing():
        modules = process_modules(Path("mypackage"), config)
        assert len(modules) > 0
    ```
    """
    modules = []
    module_names = set()
    
    for file_path in package_path.rglob("*.py"):
        if any(fnmatch.fnmatch(part, pattern) for part in file_path.parts for pattern in config.exclude_patterns):
            continue
        module_name = _get_module_name(file_path, package_path)
        module_names.add(module_name)
        modules.append({
            "name": module_name,
            "path": str(file_path),
            "ast": parse_ast(file_path),
            "internal_deps": set(),
            "imports": [],
        })

    for module in modules:
        all_imports = _find_imports(module["ast"], package_path.name)
        for imp in all_imports:
            if imp["type"] == "internal":
                parts = imp["full_path"].split(".")
                for i in range(len(parts), 0, -1):
                    candidate = ".".join(parts[:i])
                    if candidate in module_names and candidate != module["name"]:
                        module["internal_deps"].add(candidate)
                        break
        
        module["internal_deps"] = sorted(module["internal_deps"])
        module["imports"] = all_imports

    return modules


def parse_ast(file_path: Path) -> ast.AST:
    """Parse Python file to AST.
    
    Example:
        >>> ast = parse_ast(Path("module.py"))
        >>> isinstance(ast, ast.AST)
        True
    """
    with open(file_path, "r") as f:
        return ast.parse(f.read())


def get_package_metadata(
    source: str, version: Optional[str], is_local: bool
) -> Dict[str, Any]:
    """Extract package metadata from local or PyPI package."""
    if is_local:
        return get_local_metadata(Path(source))
    return get_pypi_metadata(source, version)


def get_local_metadata(path: Path) -> dict:
    """Extract package metadata with multiple fallback sources."""
    metadata = {
        "name": path.name,
        "version": "0.0.0",
        "author": "Unknown",
        "license": "Proprietary",
        "python_requires": ">=3.6",
    }

    try:
        result = subprocess.run(
            ["git", "-C", str(path), "config", "user.name"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            metadata["author"] = result.stdout.strip()
    except FileNotFoundError:
        pass

    try:
        result = subprocess.run(
            ["git", "-C", str(path), "log", "-1", "--format=%cd"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            metadata["last_updated"] = result.stdout.strip()
    except FileNotFoundError:
        pass

    license_file = next((f for f in path.glob("LICENSE*") if f.is_file()), None)
    if license_file:
        metadata["license"] = license_file.name

    try:
        pyproject_data = parse_pyproject(path / "pyproject.toml")
        metadata.update(
            {
                "name": pyproject_data["name"],
                "version": pyproject_data["version"],
                "author": pyproject_data["author"],
                "license": pyproject_data.get("license", metadata["license"]),
                "python_requires": pyproject_data.get("python_requires", ">=3.6"),
            }
        )
    except FileNotFoundError:
        pass

    return metadata


def get_pypi_metadata(name: str, version: Optional[str]) -> Dict[str, Any]:
    """Retrieve PyPI package metadata.
    
    Example:
        >>> metadata = get_pypi_metadata("requests", "2.28.0")
        >>> print(metadata["name"])
        "requests"
    """
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
        "python_requires": dist.metadata.get("Requires-Python", ">=3.6"),
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

    project = data.get("project") or data.get("tool", {}).get("poetry", {})
    return {
        "name": project.get("name", path.parent.name),
        "version": project.get("version", "0.0.0"),
        "author": (project.get("authors", [{}])[0].get("name", "Unknown")),
        "license": project.get("license", {}).get("text", "Proprietary"),
        "dependencies": project.get("dependencies", []),
        "python_requires": project.get("requires-python", ">=3.6"),
        "description": project.get("description", "No description available"),
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


def generate_docs(package_info: dict, output_path: Path, verbose: bool = False) -> None:
    """Generate documentation from analyzed package data"""
    formatter = MystWriter(config=package_info.get("config"))
    formatter.generate(package_info, output_path, verbose=verbose)


def _get_module_name(file_path: Path, package_root: Path) -> str:
    """Get clean module name from file path"""
    relative_path = file_path.relative_to(package_root)
    return str(relative_path.with_suffix("")).replace("/", ".").replace("src.", "")


def _find_imports(node: ast.AST, package_name: str) -> List[str]:
    """Improved import detection with package context"""
    imports = []
    for n in ast.walk(node):
        if isinstance(n, ast.Import):
            for alias in n.names:
                imports.append(
                    {
                        "name": alias.name,
                        "full_path": alias.name,
                        "type": (
                            "internal"
                            if alias.name.startswith(package_name)
                            else "stdlib" if "." not in alias.name else "external"
                        ),
                    }
                )
        elif isinstance(n, ast.ImportFrom):
            module = n.module or ""
            for alias in n.names:
                full_path = f"{module}.{alias.name}" if module else alias.name
                import_type = (
                    "internal" if full_path.startswith(package_name) else "external"
                )
                imports.append(
                    {"name": alias.name, "full_path": full_path, "type": import_type}
                )
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
                "returns": _get_return_type(node.returns, config),
            }
            self.generic_visit(node)

        def visit_AnnAssign(self, node):
            """Process annotated assignments."""
            if isinstance(node.target, ast.Name):
                type_info["variables"][node.target.id] = get_annotation(
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
            arg_types[arg.arg] = get_annotation(arg.annotation, config)
    return arg_types


def _get_return_type(returns: ast.AST, config: ChewdocConfig) -> str:
    """Extract return type annotation."""
    return get_annotation(returns, config) if returns else "Any"


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
                        "name": target.id,
                        "value": ast.unparse(n.value),
                        "type": (
                            get_annotation(n.annotation, config)
                            if getattr(n, "annotation", None)
                            else _infer_type_from_value(ast.unparse(n.value))
                        ),
                        "line": n.lineno,
                    }
        elif isinstance(n, ast.AnnAssign):
            if isinstance(n.target, ast.Name):
                constants[n.target.id] = {
                    "name": n.target.id,
                    "value": ast.unparse(n.value) if n.value else None,
                    "type": get_annotation(n.annotation, config),
                    "line": n.lineno,
                }
    return constants


def _find_usage_examples(node: ast.AST) -> list:
    """Extract usage examples with better detection"""
    examples = []
    
    for n in ast.walk(node):
        # Detect doctest-style examples in docstrings
        if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.Module)):
            docstring = ast.get_docstring(n)
            if docstring and any(trigger in docstring for trigger in (">>>", "Example:", "Usage:")):
                examples.append({
                    "type": "doctest",
                    "name": f"In {n.name}" if hasattr(n, 'name') else "Module-level",
                    "content": docstring,
                    "line": n.lineno
                })
        
        # Detect test functions with assert statements
        if isinstance(n, ast.FunctionDef) and n.name.lower().startswith("test"):
            test_body = "\n".join(ast.unparse(stmt) for stmt in n.body)
            examples.append({
                "type": "pytest",
                "name": n.name,
                "line": n.lineno,
                "content": f"def {n.name}():\n{test_body}"
            })
    
    return examples


def _infer_type_from_value(value: str) -> str:
    """Infer basic type from assigned value"""
    if value.startswith(('"', "'")):
        return "str"
    if value.isdigit():
        return "int"
    if value.replace(".", "", 1).isdigit():
        return "float"
    if value in ("True", "False"):
        return "bool"
    return "Any"


def _generate_basic_example(node: ast.FunctionDef) -> str:
    """Generate simple usage example for functions"""
    args = [f"{arg.arg}=..." for arg in node.args.args]
    return f"{node.name}({', '.join(args)})"


def _find_relationships(imports: list, modules: list, package_name: str) -> dict:
    """Map relationships between components using actual package name"""
    return {
        "depends_on": [imp["full_path"] for imp in imports],
        "used_by": [
            mod["name"]
            for mod in modules
            if any(f"{package_name}." in dep for dep in mod.get("internal_deps", []))
        ],
    }


def _analyze_relationships(modules: list, package_name: str) -> dict:
    """Analyze cross-module dependencies using actual package name"""
    relationship_map = defaultdict(set)

    for module in modules:
        for dep in module["internal_deps"]:
            relationship_map[module["name"]].add(dep)

    return {
        "dependency_graph": {k: sorted(v) for k, v in relationship_map.items()},
        "reverse_dependencies": {
            target: sorted({source for source, targets in relationship_map.items() if target in targets})
            for target in set().union(*relationship_map.values())
        },
    }


def _generate_usage_examples(ast_node: ast.AST) -> list:
    """Generate basic usage examples from function definitions"""
    examples = []

    class ExampleVisitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef):
            if node.name.startswith("test_") or node.name.startswith("example_"):
                example = {
                    "code": ast.unparse(node),
                    "description": (ast.get_docstring(node) or "").split("\n")[0]
                }
                self.examples.append(example)
            self.generic_visit(node)

    ExampleVisitor().visit(ast_node)
    return examples


def _infer_type_info(node: ast.Assign) -> Dict[str, str]:
    """Infer type information from assignment values"""
    if not node.value:
        return {"type": None, "value": None}

    value = ast.unparse(node.value)
    type_map = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
    }

    inferred_type = "Any"
    for type_name, type_check in type_map.items():
        try:
            if isinstance(ast.literal_eval(node.value), type_check):
                inferred_type = type_name
                break
        except (ValueError, SyntaxError):
            continue

    return {"type": inferred_type, "value": value, "inferred": True}
