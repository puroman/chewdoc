from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from chewdoc.constants import (
    META_TEMPLATE,
    MODULE_TEMPLATE,
    API_REF_TEMPLATE,
    RELATIONSHIP_TEMPLATE,
)
import ast


def generate_myst(
    package_info: Dict[str, Any],
    output_path: Path,
    template_dir: Optional[Path] = None,
    enable_cross_refs: bool = True,
) -> None:
    """Generate structured MyST documentation with separate files"""
    if not package_info:
        raise ValueError("No package data provided")

    # Create output directory structure
    package_name = package_info.get("name", "unnamed_package")
    output_dir = output_path / f"{package_name}_docs"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate main package index
    (output_dir / "index.myst").write_text(_format_package_index(package_info))

    # Generate module files
    for module in package_info.get("modules", []):
        module_name = module["name"].replace(".", "_")
        module_path = output_dir / f"{module_name}.myst"
        module_path.write_text(_format_module_content(module))

    if template_dir:
        # Load custom templates
        pass
    else:
        # Use default templates
        pass

    if enable_cross_refs:
        # Generate cross references
        pass
    else:
        # Skip cross reference generation
        pass


def _format_package_index(package_data: Dict[str, Any]) -> str:
    """Generate main package index with module links"""
    content = [
        f"# {package_data['name']} Documentation\n",
        "## Package Overview",
        META_TEMPLATE.format(**package_data),
        "\n## Modules\n",
    ]

    for module in package_data.get("modules", []):
        module_name = module["name"].replace(".", "_")
        content.append(f"- [[{module['name']}]({module_name}.myst)]")

    return "\n".join(content)


def _format_module_content(module: Dict[str, Any]) -> str:
    """Generate comprehensive module documentation with new sections"""
    content = [
        f"# {module['name']} Module",
        f"**Path**: `{module['path']}`",
        "\n## Module Metadata",
        _format_module_metadata(module),
        "\n## Imports",
        _format_imports(module.get("imports", [])),
        "\n## Constants",
        _format_constants(module.get("constants", {})),
        "\n## API Reference",
        _format_api_reference(module.get("type_info", {})),
        "\n## Usage Examples",
        _format_usage_examples(module.get("examples", [])),
        "\n## Source Code Structure",
        _format_code_structure(module.get("ast", {})),
    ]
    return "\n".join(content)


def _format_imports(imports: list) -> str:
    """Format imports with type context and source information"""
    categorized = {"stdlib": [], "internal": [], "external": []}

    for imp in imports:
        entry = f"`{imp['name']}`"
        if imp["source"]:
            entry += f" from `{imp['source']}`"

        if imp["full_path"].startswith("chewdoc."):
            categorized["internal"].append(f"- [[{imp['full_path']}|{entry}]")
        elif "." not in imp["full_path"]:
            categorized["stdlib"].append(f"- {entry}")
        else:
            categorized["external"].append(f"- {entry}")

    sections = []
    if categorized["stdlib"]:
        sections.append(
            "### Standard Library\n" + "\n".join(sorted(categorized["stdlib"]))
        )
    if categorized["internal"]:
        sections.append(
            "### Internal Dependencies\n" + "\n".join(sorted(categorized["internal"]))
        )
    if categorized["external"]:
        sections.append(
            "### External Dependencies\n" + "\n".join(sorted(categorized["external"]))
        )

    return "\n\n".join(sections) or "No imports found"


def _format_code_structure(ast_data: ast.Module) -> str:
    """Visualize code structure hierarchy"""
    structure = []

    if not isinstance(ast_data, ast.Module):
        return ""

    for item in ast_data.body:
        if isinstance(item, ast.ClassDef):
            class_entry = f"### Class: {item.name}"
            methods = [
                f"  - Method: {subitem.name}"
                for subitem in item.body
                if isinstance(subitem, ast.FunctionDef)
            ]
            if methods:
                class_entry += "\n" + "\n".join(methods)
            structure.append(class_entry)
        elif isinstance(item, ast.FunctionDef):
            structure.append(f"- Function: {item.name}")

    return "\n".join(structure)


def _format_api_reference(types: Dict[str, Any]) -> str:
    """Format functions and classes with cross-references and docstrings"""
    sections = []

    # Handle classes and their methods
    for cls_name, cls_info in types.get("classes", {}).items():
        class_doc = [
            f"## {cls_name}",
            f"[[{cls_name}]]",
            cls_info.get("doc", "No class documentation"),
        ]

        if cls_info.get("methods"):
            class_doc.append("\n**Methods**:")
            for method, details in cls_info["methods"].items():
                args = ", ".join([f"{k}: {v}" for k, v in details["args"].items()])
                class_doc.append(f"- `{method}({args})` -> {details['returns']}")

        sections.append("\n".join(class_doc))

    # Handle functions
    for func_name, func_info in types.get("functions", {}).items():
        args = ", ".join([f"{k}: {v}" for k, v in func_info["args"].items()])
        func_doc = [
            f"## `{func_name}({args})` -> {func_info['returns']}",
            func_info.get("doc", "No function documentation"),
        ]
        sections.append("\n".join(func_doc))

    return "\n\n".join(sections) or "No public API elements"


def _format_metadata(package_data: Dict[str, Any]) -> str:
    """Format package metadata section with fallbacks"""
    return META_TEMPLATE.format(
        name=package_data.get("name", "Unnamed Package"),
        version=package_data.get("version", "0.0.0"),
        author=package_data.get("author", "Unknown Author"),
        license=package_data.get("license", "Proprietary"),
        dependencies="\n  - ".join(package_data.get("dependencies", [])),
        python_requires=package_data.get("python_requires", ">=3.6"),
    )


def _format_modules(modules: list) -> str:
    """Single-line module summaries with key details"""
    return "\n".join(
        f"## {m.get('name', 'unnamed_module')}\n"
        f"{_format_docstrings(m.get('docstrings', {}))}\n"
        f"**Exports**: {_format_exports(m.get('types', {}))}\n"
        f"**Imports**: {', '.join(m.get('imports', []))}\n"
        f"{_format_relationships(m)}\n"
        f"{_format_type_info(m.get('types', {}))}\n"
        for m in modules
    )


def _format_exports(types: dict) -> str:
    """Combine all exports in one line"""
    return ", ".join(
        [*types.get("functions", {}).keys(), *types.get("classes", {}).keys()]
    )


def _format_type_info(type_info: Dict[str, Any]) -> str:
    """Ultra-compact type formatting"""
    lines = []
    if refs := type_info.get("cross_references"):
        lines.append(
            "### Type References\n" + "\n".join(f"- [[{t}]]" for t in sorted(refs))
        )

    if funcs := type_info.get("functions"):
        lines.append(
            "Functions: "
            + ", ".join(
                f"{name}{_short_sig(details)}" for name, details in funcs.items()
            )
        )

    if classes := type_info.get("classes"):
        lines.append(
            "### Classes\n"
            + "\n".join(
                f"**{cls}**\n"
                + "\n".join(
                    f"- {attr}: {type_hint}"
                    for attr, type_hint in details.get("attributes", {}).items()
                )
                for cls, details in classes.items()
            )
        )

    return "\n".join(lines)


def _short_sig(details: dict) -> str:
    return _format_function_signature(details)


def _format_type_reference(type_str: str) -> str:
    """Format type strings as links when possible"""
    parts = type_str.split("[")
    base_type = parts[0]
    if base_type in KNOWN_TYPES:
        return f"[{type_str}](#{base_type.lower()})"
    return type_str


def _format_function_signature(details: Dict[str, Any]) -> str:
    """Format complex type signatures"""
    args = [
        f"{name}: {_format_type_reference(type)}"
        for name, type in details["args"].items()
    ]
    return_type = _format_type_reference(details["returns"])
    return f"({', '.join(args)}) -> {return_type}"


def _format_docstrings(docstrings: Dict[str, str]) -> str:
    """Format extracted docstrings"""
    return "\n".join(
        f":::{{doc}} {name}\n{doc}\n:::" for name, doc in docstrings.items()
    )


def _format_relationships(module: dict) -> str:
    """Compact relationship formatting"""
    deps = [
        *(f"[[{dep}]]" for dep in module.get("internal_deps", [])),
        *(
            f"`{imp}`"
            for imp in module.get("imports", [])
            if imp not in module.get("internal_deps", [])
        ),
    ]
    return f"**Dependencies**: {', '.join(deps)}\n" if deps else ""


def _compact_imports(imports: list) -> str:
    """Compact imports formatting"""
    if not imports:
        return ""

    return "**Imports**: " + ", ".join(f"`{imp}`" for imp in imports)


def _format_module_metadata(module: Dict[str, Any]) -> str:
    """Format module-level metadata using the template"""
    try:
        # Convert timestamp to datetime object first
        timestamp = Path(module["path"]).stat().st_mtime
        last_updated = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
    except (KeyError, FileNotFoundError, OSError):
        last_updated = "Unknown date"

    # Prepare optional sections
    role_section = (
        f"- **Role**: {module.get('role', 'Unspecified')}" if module.get("role") else ""
    )
    layer_section = (
        f"- **Layer**: {module.get('layer', 'Unspecified')}"
        if module.get("layer")
        else ""
    )

    # Format dependencies
    dependencies = []
    for imp in module.get("imports", []):
        if isinstance(imp, dict):
            name = imp.get("name", "")
            source = imp.get("source", "")
            if source:
                dependencies.append(f"{name} -> {source}")
            else:
                dependencies.append(name)
        else:
            dependencies.append(str(imp))
    deps_str = "\n    ".join(dependencies) if dependencies else "No dependencies"

    # Format usage examples
    examples = []
    for ex in module.get("examples", []):
        if isinstance(ex, dict):
            if ex.get("type") == "doctest":
                examples.append(ex.get("content", ""))
            elif ex.get("type") == "pytest":
                examples.append(ex.get("body", ""))
        else:
            examples.append(str(ex))
    examples_str = "\n\n".join(examples) if examples else "No examples available"

    return MODULE_TEMPLATE.format(
        name=module["name"],
        package=module.get("package", "unknown"),
        description=module.get("docstrings", {})
        .get("Module:module", {})
        .get("doc", "No description"),
        role_section=role_section,
        layer_section=layer_section,
        dependencies=deps_str,
        usage_examples=examples_str,
    )


def _format_constants(constants: Dict[str, Any]) -> str:
    """Format module constants section"""
    if not constants:
        return "No constants defined"

    return "### Constants\n" + "\n".join(
        f"- `{name}` ({info['type'] or 'inferred'}): {info['value']}"
        for name, info in constants.items()
    )


def _format_usage_examples(examples: list) -> str:
    """Format usage examples section"""
    if not examples:
        return "No usage examples found"

    sections = []
    for ex in examples:
        if ex["type"] == "doctest":
            sections.append(f"```python\n{ex['content']}\n```")
        elif ex["type"] == "pytest":
            sections.append(
                f"**Test Case**: {ex['name']}\n```python\n{ex['body']}\n```"
            )

    return "### Usage Examples\n" + "\n\n".join(sections)
