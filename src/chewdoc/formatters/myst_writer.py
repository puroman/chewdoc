from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from chewdoc.utils import get_annotation, infer_responsibilities
from chewdoc.config import ChewdocConfig

import ast
import click

from chewdoc.constants import META_TEMPLATE, MODULE_TEMPLATE


class MystWriter:
    def __init__(self, config: Optional[ChewdocConfig] = None):
        self.config = config or ChewdocConfig()
        self.config.max_example_lines = getattr(self.config, 'max_example_lines', 15)  # Add default

    def generate(self, package_data: dict, output_path: Path, verbose: bool = False) -> None:
        """Generate structured MyST documentation with separate files"""
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
            package=module["package"],
            role_section=self._format_role(module),
            layer_section=self._format_architecture_layer(module),
            description=module.get("description") or infer_responsibilities(module),
            dependencies=self._format_dependencies(module["internal_deps"]),
            usage_examples=self._format_usage_examples(
                module.get("examples", []), 
                config=module.get("config")  # Pass config from module data
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

    def _format_dependencies(self, deps: list) -> str:
        """Format internal dependencies as Mermaid graph"""
        if not deps:
            return "No internal dependencies"
        
        nodes = []
        links = []
        for i, dep in enumerate(sorted(deps)):
            nodes.append(f"    N{i}[{dep}]")
            links.append(f"    N{i} -->|uses| {dep.replace('.', '_')}")
        
        return "graph TD\n" + "\n".join(nodes + links)

    def _format_modules(self, modules: list) -> str:
        """Format module list for index page"""
        return "\n".join(f"- [[{m['name']}]]" for m in modules)

    def _format_function_signature(self, args: ast.arguments, returns: ast.AST) -> str:
        """Format function signature with type annotations"""
        params = []
        for arg in args.args:
            name = arg.arg
            annotation = get_annotation(arg.annotation, self.config) if arg.annotation else ""
            params.append(f"{name}{': ' + annotation if annotation else ''}")

        return_type = get_annotation(returns, self.config) if returns else ""
        if return_type:
            return f"({', '.join(params)}) -> {return_type}"
        return f"({', '.join(params)})"

    def _format_usage_examples(self, examples: list, config: ChewdocConfig) -> str:
        """Format usage examples with proper code blocks"""
        if not examples:
            return "No usage examples available"
        
        formatted = []
        for idx, example in enumerate(examples[:3], 1):  # Show max 3 examples
            code = example.get("code", "")
            
            # Trim long examples
            lines = code.split("\n")
            if len(lines) > config.max_example_lines:
                code = "\n".join(lines[:config.max_example_lines]) 
                code += f"\n# ... truncated {len(lines)-config.max_example_lines} lines"
            
            desc = example.get("description", "")
            if desc:
                desc = f"*{desc}*"
                
            formatted.append(
                f"### Example {idx}\n"
                f"{desc}\n"
                f"```python\n{code}\n```"
            )
        
        return "\n\n".join(formatted)
