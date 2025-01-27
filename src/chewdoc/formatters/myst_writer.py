from pathlib import Path
from typing import Dict, Any
from chewdoc.constants import META_TEMPLATE, MODULE_TEMPLATE, API_REF_TEMPLATE, RELATIONSHIP_TEMPLATE

KNOWN_TYPES = {"List", "Dict", "Optional", "Union"}  # Basic Python types

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
    """Format modules section with fallbacks"""
    if not modules:
        return "\nNo modules found in package\n"
    
    sections = []
    for module in modules:
        sections.append(MODULE_TEMPLATE.format(
            name=module.get("name", "Unnamed Module"),
            description=_format_docstrings(module.get("docstrings", {})),
            dependencies="\n".join([f"- {imp}" for imp in module.get("imports", [])])
        ))
        sections.append(_format_type_info(module["types"]))
        sections.append(f"\n**Source**: `{module['path']}`\n")
        sections.append(_format_relationships(module))
    return "\n".join(sections)

def _format_type_info(type_info: Dict[str, Any]) -> str:
    """Add cross-references section"""
    sections = []
    
    if type_info["cross_references"]:
        sections.append("\n### Type References\n")
        sections.extend(f"- [[{t}]]" for t in sorted(type_info["cross_references"]))
    
    # Format functions
    for func, details in type_info["functions"].items():
        sections.append(API_REF_TEMPLATE.format(
            name=func,
            signature=_format_function_signature(details),
            doc=""
        ))
    
    # Format classes only if they exist
    if type_info["classes"]:
        for cls, details in type_info["classes"].items():
            sections.append(f":::{cls}")
            for attr, type_hint in details["attributes"].items():
                sections.append(f"- {attr}: {type_hint}")
            sections.append(":::")
    
    return "\n".join(sections)

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
    """Format module dependency relationships"""
    internal_deps = module.get("internal_deps", [])
    imports = module.get("imports", [])
    
    internal = "\n".join(f"- [[{dep}]]" for dep in internal_deps)
    external = "\n".join(f"- `{dep}`" for dep in imports if dep not in internal_deps)
    
    return RELATIONSHIP_TEMPLATE.format(
        dependencies=internal or "No internal dependencies",
        external=external or "No external dependencies"
    ) 