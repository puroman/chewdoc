from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from chewdoc.utils import get_annotation, infer_responsibilities, format_function_signature
from chewdoc.config import ChewdocConfig

import ast
import click
import fnmatch
import re
import logging

from chewdoc.constants import META_TEMPLATE, MODULE_TEMPLATE

logger = logging.getLogger(__name__)


class MystWriter:
    def __init__(self, config: Optional[ChewdocConfig] = None):
        self.config = config or ChewdocConfig()
        self.package_data = {}
        self.config.max_example_lines = getattr(self.config, 'max_example_lines', 15)  # Add default

    def generate(self, package_data: Dict[str, Any], output_path: Path, verbose: bool = False) -> None:
        """Generate documentation files"""
        self.package_data = package_data
        self.current_module = {}  # Track current module context
        index_content = self._format_package_index(package_data)
        
        # Ensure required fields with safe defaults
        package_data.setdefault("name", "Unknown Package")
        package_data.setdefault("package", package_data["name"])
        package_data.setdefault("version", "0.0.0")
        package_data.setdefault("author", "Unknown")
        package_data.setdefault("license", "Not specified")
        package_data.setdefault("python_requires", ">=3.6")
        
        # Handle directory output path
        output_dir = output_path if output_path.is_dir() else output_path.parent
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate module files
        for mod in package_data["modules"]:
            self.current_module = mod.copy()  # Set module context
            module = mod if isinstance(mod, dict) else {"name": str(mod)}
            module_file = output_dir / f"{module['name']}.md"
            content = self._format_module(module)
            module_file.write_text(content)

        # Generate index file
        (output_dir / "index.md").write_text(index_content)

    def _format_package_index(self, package_data: Dict[str, Any]) -> str:
        """Generate main package index with module links"""
        content = [
            f"# {package_data.get('name', package_data['package'])} Documentation\n",
            "## Package Overview",
            self._format_metadata(package_data),
            "\n## Modules\n"
        ]
        
        for mod in package_data["modules"]:
            # Ensure module is always a dictionary
            module_data = mod if isinstance(mod, dict) else {"name": str(mod)}
            self.current_module = module_data.copy()
            content.append(f"- [{module_data['name']}]({module_data['name']}.md)")
        
        return "\n".join(content)

    def _format_module_content(self, module: dict) -> str:
        """Format module docs with package context"""
        module = module.copy()
        module.setdefault("type_info", {})
        module.setdefault("examples", [])
        module.setdefault("docstrings", {})
        try:
            return MODULE_TEMPLATE.format(
                name=module["name"],
                package=self.package_data["package"],
                role_section=self._format_role(module),
                layer_section=self._format_architecture_layer(module),
                imports_section=self._format_imports(module.get("imports", []), self.package_data["package"]),
                description=self._get_module_description(module),
                dependencies=self._format_dependencies(module["internal_deps"]),
                usage_examples=self._format_usage_examples(
                    module.get("examples", []), 
                    config=self.config
                ),
                api_reference=self._format_api_reference(module.get("type_info", {}))
            )
        except ValueError as e:
            raise ValueError(
                f"Failed to process module {module['name']}: {str(e)}"
            ) from e

    def _format_imports(self, imports: list, package_name: str) -> str:
        """Format imports using actual package context"""
        categorized = {"stdlib": [], "internal": [], "external": []}
        
        # Add cross-references first
        for ref in self.current_module.get("type_info", {}).get("cross_references", []):
            categorized["internal"].append(f"- [[{ref}]]")

        # Then process regular imports
        for imp in imports:
            if isinstance(imp, str):
                imp = {"name": imp, "full_path": imp, "source": ""}
            
            entry = f"`{imp['name']}`"
            if imp.get("source"):
                entry += f" from `{imp['source']}`"

            if imp["full_path"].startswith(f"{package_name}."):
                categorized["internal"].append(f"- [[{imp['full_path']}|{entry}]]")
            elif "." not in imp["full_path"]:
                categorized["stdlib"].append(f"- {entry}")
            else:
                categorized["external"].append(f"- {entry}")

        sections = []
        if categorized["stdlib"]:
            sections.append("### Standard Library\n" + "\n".join(sorted(categorized["stdlib"])))
        if categorized["internal"]:
            sections.append("### Internal Dependencies\n" + "\n".join(sorted(categorized["internal"])))
        if categorized["external"]:
            sections.append("### External Dependencies\n" + "\n".join(sorted(categorized["external"])))
        
        return "\n\n".join(sections) if sections else "No imports"

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

    def _format_api_reference(self, types: dict) -> str:
        """Format functions and classes with cross-references"""
        sections = []
        
        # Handle functions first
        for func_name, func_info in types.get("functions", {}).items():
            signature = self._format_function_signature(func_info)
            sections.append(f"## `{func_name}{signature}`")
            if func_info.get("doc"):
                sections.append(f"\n{func_info['doc']}\n")

        # Handle classes 
        for cls_name, cls_info in types.get("classes", {}).items():
            class_section = self._format_class(cls_name, cls_info)
            sections.append(class_section)
        
        return "\n\n".join(sections)

    def _format_metadata(self, package_data: Dict[str, Any]) -> str:
        """Format package metadata with fallback values"""
        return META_TEMPLATE.format(
            name=package_data.get('name', package_data.get('package', 'Unnamed Package')),
            version=package_data.get('version', '0.0.0'),
            author=package_data.get('author', 'Unknown Author'),
            license=package_data.get('license', 'Not specified'),
            dependencies=", ".join(package_data.get("dependencies", ["None"])),
            python_requires=package_data.get("python_requires", "Not specified")
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

    def _format_function_signature(self, func_info: dict) -> str:
        """Format function signature handling serialized AST data."""
        args_data = func_info.get('args')
        return_data = func_info.get('returns')
        
        # Handle serialized AST data
        return format_function_signature(
            args=args_data,
            returns=return_data,
            config=self.config
        )

    def _format_usage_examples(self, examples: list) -> str:
        output = []
        for idx, ex in enumerate(examples, 1):
            try:
                if isinstance(ex, dict):
                    code = ex.get('code') or ex.get('content', '')
                elif isinstance(ex, str):
                    code = ex
                else:
                    logger.warning(f"Skipping invalid example type: {type(ex).__name__}")
                    continue
                if code:
                    output.append(f"```python\n{code}\n```")
            except Exception as e:
                logger.warning(f"Failed to process example #{idx}: {str(e)}")
        return '\n'.join(output)

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

    def _get_module_description(self, module: dict) -> str:
        """Extract module description from docstrings"""
        if "docstrings" in module and "module:1" in module["docstrings"]:
            return module["docstrings"]["module:1"]
        return infer_responsibilities(module)

    def _format_module(self, module: dict) -> str:
        """Format module documentation with error resilience"""
        content = [f"# {module['name']}\n```{{module}} {module['name']}\n"]
        
        # Handle examples safely
        if module.get('examples'):
            content.append("\n## Examples\n")
            for example in module['examples']:
                try:
                    code = example.get('code') or example.get('content') or str(example)
                    content.append(f"```python\n{code}\n```\n")
                except Exception as e:
                    logger.error(f"Failed to format example: {e}")
                    continue
        
        return "\n".join(content)

    def _format_classes(self, classes: dict) -> str:
        output = []
        for class_name, class_info in classes.items():
            output.append(f"## {class_name}\n")
            if class_info.get('docstring'):
                output.append(f"\n{class_info['docstring']}\n")
            
            # Format methods
            if class_info.get('methods'):
                output.append("\n### Methods\n")
                for method_name, method_info in class_info['methods'].items():
                    output.append(f"#### {method_name}{self._format_function_signature(method_info)}\n")
                    if method_info.get('docstring'):
                        output.append(f"\n{method_info['docstring']}\n")
        return "\n".join(output)

    def _format_class(self, cls_name: str, cls_info: dict) -> str:
        """Format class documentation with methods"""
        content = [f"## {cls_name}"]  # Header without cross-reference
        content.append(f"[[{cls_name}]]\n")  # Add cross-reference as separate line
        if cls_info.get("doc"):
            content.append(f"\n{cls_info['doc']}\n")
        
        if cls_info.get("methods"):
            content.append("### Methods")
            for method_name, method_info in cls_info["methods"].items():
                try:
                    signature = self._format_function_signature(method_info)
                    content.append(f"#### `{method_name}{signature}`")
                    if method_info.get("doc"):
                        content.append(f"\n{method_info['doc']}\n")
                except Exception as e:
                    raise ValueError(f"Error formatting method {method_name}") from e
        
        return "\n".join(content)

    def _format_function(self, func_name: str, func_data: dict) -> str:
        if not isinstance(func_data.get('args'), (ast.arguments, dict)):
            raise ValueError(f"Invalid function arguments for {func_name}")
        args = func_data['args']
        returns = func_data.get('returns')
        return f"`{func_name}{_format_signature(args, returns)}`"

def generate_docs(package_info: dict, output_path: Path) -> None:
    writer = MystWriter()
    writer.generate(package_info, output_path)
