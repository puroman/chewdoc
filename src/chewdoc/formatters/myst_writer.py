from pathlib import Path
from typing import Dict, Any
from chewdoc.constants import META_TEMPLATE, MODULE_TEMPLATE, API_REF_TEMPLATE, RELATIONSHIP_TEMPLATE

KNOWN_TYPES = {"List", "Dict", "Optional", "Union", "Sequence", "Iterable"}  # Basic Python types

def generate_myst(package_data: Dict[str, Any], output_path: Path) -> None:
    """Generate MyST documentation with validation"""
    if not package_data:
        raise ValueError("No package data provided")
    
    content = [
        f"# Package: {package_data.get('name', 'Unnamed Package')}\n",
        _format_metadata(package_data),
        _format_modules(package_data.get("modules", []))
    ]
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(content))

def _format_metadata(package_data: Dict[str, Any]) -> str:
    """Format package metadata section with fallbacks"""
    return META_TEMPLATE.format(
        name=package_data.get("name", "Unnamed Package"),
        version=package_data.get("version", "0.0.0"),
        author=package_data.get("author", "Unknown Author"),
        license=package_data.get("license", "Proprietary"),
        dependencies="\n  - ".join(package_data.get("dependencies", [])),
        python_requires=package_data.get("python_requires", ">=3.6")
    )

def _format_modules(modules: list) -> str:
    """Single-line module summaries with key details"""
    return "\n".join(
        f"## {m.get('name', 'unnamed_module')}\n"
        f"{_format_docstrings(m.get('docstrings', {}))}\n"
        f"**Exports**: {_format_exports(m.get('types', {}))}\n" 
        f"**Imports**: {', '.join(m.get('imports', []))}\n"
        for m in modules
    )

def _format_exports(types: dict) -> str:
    """Combine all exports in one line"""
    return ", ".join([
        *types.get("functions", {}).keys(),
        *types.get("classes", {}).keys()
    ])

def _format_type_info(type_info: Dict[str, Any]) -> str:
    """Ultra-compact type formatting"""
    lines = []
    if refs := type_info.get("cross_references"):
        lines.append(f"Types: {', '.join(sorted(refs))}")
    
    if funcs := type_info.get("functions"):
        lines.append("Functions: " + ", ".join(
            f"{name}{_short_sig(details)}" 
            for name, details in funcs.items()
        ))
    
    if classes := type_info.get("classes"):
        lines.append("Classes: " + ", ".join(
            f"{cls}({', '.join(details['attributes'])})"
            for cls, details in classes.items()
        ))
    
    return "\n".join(lines)

def _short_sig(details: dict) -> str:
    return f"({len(details['args'])} args) -> {details['returns']}"

def _format_type_reference(type_str: str) -> str:
    """Format type strings as links when possible"""
    parts = type_str.split("[")
    base_type = parts[0]
    if base_type in KNOWN_TYPES:
        return f"[{type_str}](#{base_type.lower()})"
    return type_str

def _format_function_signature(details: Dict[str, Any]) -> str:
    """Format complex type signatures"""
    args = [f"{name}: {_format_type_reference(type)}" 
            for name, type in details["args"].items()]
    return_type = _format_type_reference(details["returns"])
    return f"({', '.join(args)}) -> {return_type}"

def _format_docstrings(docstrings: Dict[str, str]) -> str:
    """Format extracted docstrings"""
    return "\n".join(
        f":::{{doc}} {name}\n{doc}\n:::"
        for name, doc in docstrings.items()
    )

def _format_relationships(module: dict) -> str:
    """Compact relationship formatting"""
    deps = [
        *(f"[[{dep}]]" for dep in module.get("internal_deps", [])),
        *(f"`{imp}`" for imp in module.get("imports", []) 
          if imp not in module.get("internal_deps", []))
    ]
    return f"**Dependencies**: {', '.join(deps)}\n" if deps else ""

def _compact_imports(imports: list) -> str:
    """Compact imports formatting"""
    if not imports:
        return ""
    
    return "**Imports**: " + ", ".join(f"`{imp}`" for imp in imports) 