from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from chewdoc.utils import get_annotation, infer_responsibilities, format_function_signature
from chewdoc.config import ChewdocConfig

import ast
import click
import fnmatch

from chewdoc.constants import META_TEMPLATE, MODULE_TEMPLATE


class MystWriter:
    def __init__(self, config: Optional[ChewdocConfig] = None):
        self.config = config or ChewdocConfig()
        self.config.max_example_lines = getattr(self.config, 'max_example_lines', 15)  # Add default

    def generate(self, package_data: dict, output_path: Path, verbose: bool = False) -> None:
        """Generate structured MyST documentation with separate files"""
        self.package_data = package_data
        start_time = datetime.now()
        if verbose:
            click.echo(f"📄 Starting MyST generation at {start_time:%H:%M:%S}")
            click.echo(f"📂 Output directory: {output_path}")

        if not package_data:
            raise ValueError("No package data provided")

        # Create output directory structure
        package_name = package_data.get("name", "unnamed_package").split(".")[-1]
        output_dir = output_path / f"{package_name}_docs"
        output_dir.mkdir(parents=True, exist_ok=True)
        main_output = output_dir / "index.myst"

        # Generate main package index
        main_output.write_text(self._format_package_index(package_data))

        # Generate module files
        module_count = len(package_data.get("modules", []))
        for idx, module in enumerate(package_data.get("modules", []), 1):
            if verbose:
                click.echo(f"📝 Processing module {idx}/{module_count}: {module['name']}")
            module_name = module["name"].split(".src.")[-1].replace(".", "_")
            module["config"] = self.config  # Inject config into module data
            module_path = output_dir / f"{module_name}.myst"
            module_path.write_text(self._format_module_content(module))

        if verbose:
            duration = datetime.now() - start_time
            click.echo(f"✅ Documentation generated in {duration.total_seconds():.3f}s")
            click.echo(f"📑 Created {len(package_data.get('modules', []))} module files")
            click.echo(f"📂 Output location: {output_dir.resolve()}")

        # Add debug output
        if verbose:
            click.echo("\n[DEBUG] Final package data structure:")
            click.echo(f"Modules: {len(package_data.get('modules', []))}")
            for mod in package_data.get("modules", [])[:3]:
                click.echo(f"\nModule: {mod['name']}")
                click.echo(f"Package: {package_data['package']}")
                click.echo(f"Constants: {list(mod.get('constants', {}).keys())[:3]}...")
                click.echo(f"Dependencies: {mod.get('internal_deps', [])[:3]}...")
                click.echo(f"Examples: {len(mod.get('examples', []))}")

    def _format_package_index(self, package_data: Dict[str, Any]) -> str:
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

    def _format_module_content(self, module: dict) -> str:
        """Format module docs with package context"""
        return MODULE_TEMPLATE.format(
            name=module["name"],
            package=self.package_data["package"],
            role_section=self._format_role(module),
            layer_section=self._format_architecture_layer(module),
            description=module.get("description") or infer_responsibilities(module),
            dependencies=self._format_dependencies(module["internal_deps"]),
            usage_examples=self._format_usage_examples(
                module.get("examples", []), 
                config=self.config
            ),
        )

    def _format_imports(self, imports: list, package_name: str) -> str:
        """Format imports using actual package context"""
        categorized = {"stdlib": [], "internal": [], "external": []}

        for imp in imports:
            entry = f"`{imp['name']}`"
            if imp["source"]:
                entry += f" from `{imp['source']}`"

            if imp["full_path"].startswith(f"{package_name}."):
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

    def _format_code_structure(self, ast_data: ast.Module) -> str:
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

    def _format_api_reference(self, types: Dict[str, Any]) -> str:
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
                    signature = self._format_function_signature(
                        details["args"], 
                        details["returns"]
                    )
                    class_doc.append(f"- `{method}{signature}`")

        # Handle functions
        for func_name, func_info in types.get("functions", {}).items():
            signature = self._format_function_signature(
                func_info["args"], 
                func_info["returns"]
            )
            func_doc = [
                f"## `{func_name}{signature}`",
                func_info.get("doc", "No function documentation"),
            ]
            sections.append("\n".join(func_doc))

        return "\n\n".join(sections) or "No public API elements"

    def _format_metadata(self, package_data: Dict[str, Any]) -> str:
        """Format package metadata section with fallbacks"""
        return META_TEMPLATE.format(
            name=package_data.get("name", "Unnamed Package"),
            version=package_data.get("version", "0.0.0"),
            author=package_data.get("author", "Unknown Author"),
            license=package_data.get("license", "Proprietary"),
            dependencies="\n  - ".join(package_data.get("dependencies", [])),
            python_requires=package_data.get("python_requires", ">=3.6"),
        )

    def _format_role(self, module: dict) -> str:
        """Format module role description"""
        if "role" in module:
            return f"- **Role**: {module['role']}"
        return "- **Role**: General purpose module"

    def _format_architecture_layer(self, module: dict) -> str:
        """Format module architecture layer information"""
        if "layer" in module:
            return f"- **Architecture Layer**: {module['layer']}"
        return "- **Architecture Layer**: Not specified"

    def _format_dependencies(self, dependencies: list) -> str:
        """Format module dependencies as Mermaid graph"""
        if not dependencies:
            return "No internal dependencies"
        
        connections = []
        seen = set()
        
        for dep in dependencies:
            clean_dep = self._clean_node_name(dep)
            if clean_dep not in seen:
                connections.append(f"{clean_dep}[{dep}]")
                seen.add(clean_dep)
        
        return "\n    ".join(connections[:10])  # Show first 10 deps

    def _clean_node_name(self, name: str) -> str:
        """Sanitize node names for Mermaid compatibility"""
        return name.replace(".", "_").replace("-", "_")

    def _format_modules(self, modules: list) -> str:
        """Format module list for index page"""
        return "\n".join(f"- [[{m['name']}]]" for m in modules)

    def _format_function_signature(self, args: ast.arguments, returns: ast.AST) -> str:
        """Format function signature using shared utility"""
        return format_function_signature(args, returns, self.config)

    def _format_usage_examples(self, examples: list, config: ChewdocConfig) -> str:
        """Format usage examples section"""
        if not examples:
            return "No usage examples found"
            
        output = ["## Usage Examples"]
        for ex in examples:
            if ex["type"] == "doctest":
                output.append(f"```python\n{ex['content']}\n```")
            elif ex["type"] == "pytest":
                output.append(f"**Test case**: `{ex['name']}`\n```python\n{ex['content']}\n```")
        
        return "\n\n".join(output)

    def extract_docstrings(self, node: ast.AST) -> Dict[str, str]:
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
                            "context": self._get_code_context(child),
                        }
                except Exception as e:
                    continue
        return docs
