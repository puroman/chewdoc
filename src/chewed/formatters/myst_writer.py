from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from chewed.utils import (
    get_annotation,
    infer_responsibilities,
    format_function_signature,
)
from chewed.config import chewedConfig

import ast
import click
import fnmatch
import re
import logging

from chewed.constants import META_TEMPLATE, MODULE_TEMPLATE

logger = logging.getLogger(__name__)


class MystWriter:
    def __init__(self, config: Optional[chewedConfig] = None):
        self.config = config or chewedConfig()
        self.logger = logging.getLogger(__name__)
        self.package_data = {}
        self.current_module = {}  # Initialize here instead of in generate()
        # Set default if not present in config
        if not hasattr(self.config, "max_example_lines"):
            self.config.max_example_lines = 15

    def generate(self, package_data: dict, output_path: Path) -> None:
        """Generate documentation with proper path handling"""
        output_path = output_path.resolve()
        output_path.mkdir(parents=True, exist_ok=True)

        # Write index first
        index_path = output_path / "index.md"
        index_path.write_text(self._format_index(package_data))

        # Process modules with path validation
        for mod in package_data.get("modules", []):
            module = mod if isinstance(mod, dict) else {"name": str(mod)}
            module_name = module.get("name", "unknown")

            # Sanitize module path components
            safe_path = module_name.replace(".", "/").lstrip("/")
            safe_path = safe_path.replace(
                "..", ""
            )  # Remove parent directory references
            module_file = output_path / f"{safe_path}.md"

            # Ensure parent directory exists
            module_file.parent.mkdir(parents=True, exist_ok=True)

            try:
                content = self._format_module_content(module)
                module_file.write_text(content)
            except Exception as e:
                self.logger.error(
                    f"Error generating docs for module {module_name}: {str(e)}"
                )
                continue

    def _format_index(self, package_data: dict) -> str:
        """Generate package index content"""
        content = [
            f"# {package_data['package']} Documentation\n",
            "```{toctree}\n:maxdepth: 2\n\n",
        ]
        for mod in package_data["modules"]:
            module = mod if isinstance(mod, dict) else {"name": str(mod)}
            content.append(f"{module['name'].replace('.', '/')}\n")
        content.append("```")
        return "\n".join(content)

    def _format_package_index(self, package_data: Dict[str, Any]) -> str:
        """Generate main package index with module links"""
        content = [
            f"# {package_data.get('name', package_data['package'])} Documentation\n",
            "## Package Overview",
            self._format_metadata(package_data),
            "\n## Modules\n",
        ]

        for mod in package_data["modules"]:
            # Ensure module is always a dictionary
            module_data = mod if isinstance(mod, dict) else {"name": str(mod)}
            self.current_module = module_data.copy()
            content.append(f"- [{module_data['name']}]({module_data['name']}.md)")

        return "\n".join(content)

    def _format_module_content(self, module: dict) -> str:
        """Format module docs with fallback content"""
        try:
            output = [
                f"# Module: {module['name']}\n",
                "```{py:module} " + module["name"],
            ]

            # Add class section
            if classes := module.get("type_info", {}).get("classes"):
                output.append("\n## Classes\n")
                for cls_name, cls_info in classes.items():
                    output.append(self._format_class(cls_name, cls_info))

            # Handle different docstring formats
            docstrings = module.get("docstrings", {})
            if "module" in docstrings:  # Direct module docstring
                output.append(f"\n{docstrings['module']}")
            elif "module:1" in docstrings:  # Legacy format
                output.append(f"\n{docstrings['module:1']}")
            else:
                output.append("\nNo module docstring available")

            output.append("\n```\n")
            output.append(self._format_role_section(module))

            # Add variables section
            if variables := module.get("type_info", {}).get("variables"):
                output.append("\n### Variables\n")
                for var_name, var_value in variables.items():
                    value = (
                        var_value.get("value")
                        if isinstance(var_value, dict)
                        else var_value
                    )
                    output.append(f"- `{var_name}`: {value}")

            # Add functions section
            if functions := module.get("type_info", {}).get("functions"):
                output.append("\n## Functions\n")
                for func_name, func_info in functions.items():
                    output.append(self._format_function(func_name, func_info))

            return "\n".join(output)
        except Exception as e:
            self.logger.error(f"Error formatting module {module['name']}: {str(e)}")
            return f"# Module: {module['name']}\n\nError generating documentation"

    def _format_imports(self, imports: list, package: str) -> str:
        """Categorize imports with full path handling"""
        stdlib_imports = set()
        int_imports = set()
        ext_imports = set()

        for imp in imports:
            if imp["source"].startswith(package):
                # Internal dependency - create crosslink
                int_imports.add(f"[[{imp['full_path']}|`{imp['name']}`]]")
            elif not imp["source"]:  # Standard library
                stdlib_imports.add(f"`{imp['full_path']}`")
            else:
                # External dependency - show full path
                ext_imports.add(f"`{imp['full_path']}` from `{imp['source']}`")

        sections = []
        if stdlib_imports:
            sections.append(
                "### Standard Library\n" + "\n".join(sorted(stdlib_imports))
            )
        if int_imports:
            sections.append(
                "### Internal Dependencies\n" + "\n".join(sorted(int_imports))
            )
        if ext_imports:
            sections.append(
                "### External Dependencies\n" + "\n".join(sorted(ext_imports))
            )

        return "\n\n".join(sections)

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
            name=package_data.get(
                "name", package_data.get("package", "Unnamed Package")
            ),
            version=package_data.get("version", "0.0.0"),
            author=package_data.get("author", "Unknown Author"),
            license=package_data.get("license", "Not specified"),
            dependencies=", ".join(package_data.get("dependencies", ["None"])),
            python_requires=package_data.get("python_requires", "Not specified"),
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
        """Robust signature formatting with error context"""
        try:
            args = func_info.get("args")
            returns = func_info.get("returns")
            config = self.config

            if isinstance(args, ast.arguments):
                return format_function_signature(args, returns, config)

            if isinstance(args, dict):
                args_list = args.get("args", [])
                if not isinstance(args_list, list):
                    return f"()  # Invalid arguments: {str(args)[:50]}"

                return format_function_signature(
                    ast.arguments(
                        args=[ast.arg(arg=str(arg)) for arg in args_list],
                        defaults=args.get("defaults", []),
                    ),
                    returns,
                    config,
                )

            return "()  # Unable to parse arguments"

        except Exception as e:
            error_msg = f"Error formatting signature: {str(e)[:100]}"
            self.logger.warning(error_msg)
            return f"()  # {error_msg}"

    def _validate_example(self, example: Any) -> Optional[Dict[str, str]]:
        """Robust example validation with detailed logging"""
        # Handle primitive types
        if isinstance(example, (str, int, float, bool)):
            return {"code": str(example)}

        # Handle dictionary examples
        if isinstance(example, dict):
            # Check for code/content
            code = example.get("code") or example.get("content")
            if code:
                return {"code": str(code)}

            self.logger.warning(f"Skipping example: Missing 'code'/'content' field")
            return None

        # Invalid example type
        self.logger.warning(f"Skipping invalid example type: {type(example).__name__}")
        return None

    def _format_usage_examples(self, examples: List[Any]) -> str:
        """Format usage examples with comprehensive validation"""
        valid_examples = []

        for example in examples:
            validated_example = self._validate_example(example)
            if validated_example:
                valid_examples.append(validated_example["code"])
            else:
                valid_examples.append(f"# Invalid example: {type(example).__name__}")

        return (
            "\n".join(valid_examples) if valid_examples else "No valid examples found"
        )

    def extract_docstrings(self, node: ast.AST) -> Dict[str, str]:
        """Enhanced docstring extraction with context tracking"""
        docs = {}
        for child in ast.walk(node):
            if isinstance(child, (ast.Module, ast.ClassDef, ast.FunctionDef)):
                try:
                    docstring = ast.get_docstring(child, clean=True)
                    if docstring:
                        key = (
                            f"{type(child).__name__}:{getattr(child, 'name', 'module')}"
                        )
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
        """Format a module's documentation"""
        try:
            self.logger.debug(
                f"Module data for {module.get('name')}: {module}"
            )  # Add debug logging

            # Get module docstring from the correct key
            module_doc = (
                module.get("docstrings", {}).get("module:1")
                or module.get("docstrings", {}).get("module")
                or "No module docstring available"
            )

            content = [
                f"# Module: {module['name']}\n",
                f"```{{py:module}} {module['name']}",
                module_doc,
                "```\n\n",
            ]

            # Add imports section
            if module.get("imports"):
                content.extend(
                    [
                        "## Dependencies\n",
                        self._format_imports(
                            module["imports"], self.package_data.get("package", "")
                        ),
                        "\n",
                    ]
                )

            # Add module role and architecture layer
            content.extend(
                [
                    self._format_role(module),
                    self._format_architecture_layer(module),
                    "\n",
                ]
            )

            # Add examples section if available
            if module.get("examples"):
                content.extend(
                    ["## Examples\n", self._format_usage_examples(module["examples"])]
                )

            # Add API Reference section if there are classes or functions
            type_info = module.get("type_info", {})
            if type_info.get("classes") or type_info.get("functions"):
                content.append("\n## API Reference\n\n")  # Add line break after header

                # Add variables
                if type_info.get("variables"):
                    content.append("### Variables\n")
                    for var_name, var_info in type_info["variables"].items():
                        # Handle different variable info formats
                        var_value = (
                            var_info.get("value")
                            if isinstance(var_info, dict)
                            else str(var_info)
                        )
                        content.append(f"- `{var_name}`: {var_value or 'Unknown'}")
                    content.append("")

                # Add classes
                if type_info.get("classes"):
                    for cls_name, cls_info in type_info["classes"].items():
                        content.append(f"### [[{cls_name}]]\n")
                        if cls_info.get("doc"):
                            content.append(cls_info["doc"])
                        if cls_info.get("methods"):
                            content.append("\n#### Methods")
                            for method_name, method_info in cls_info["methods"].items():
                                content.append(f"\n##### {method_name}")
                                if method_info.get("doc"):
                                    content.append(method_info["doc"])
                        content.append("")

                # Add functions
                if type_info.get("functions"):
                    for func_name, func_info in type_info["functions"].items():
                        content.append(self._format_function(func_name, func_info))

            # Add variables section outside of API Reference if only variables exist
            elif type_info.get("variables"):
                content.append("\n### Variables\n")
                for var_name, var_info in type_info["variables"].items():
                    # Handle different variable info formats
                    var_value = (
                        var_info.get("value")
                        if isinstance(var_info, dict)
                        else str(var_info)
                    )
                    content.append(f"- `{var_name}`: {var_value or 'Unknown'}")
                content.append("")

            return "\n".join(content)
        except ValueError as e:
            raise ValueError(
                f"Failed to format module {module.get('name', 'unknown')}: {str(e)}"
            )
        except Exception as e:
            raise ValueError(
                f"Unexpected error formatting module {module.get('name', 'unknown')}: {str(e)}"
            )

    def _format_classes(self, classes: dict) -> str:
        output = []
        for class_name, class_info in classes.items():
            output.append(f"## {class_name}\n")
            if class_info.get("docstring"):
                output.append(f"\n{class_info['docstring']}\n")

            # Format methods
            if class_info.get("methods"):
                output.append("\n### Methods\n")
                for method_name, method_info in class_info["methods"].items():
                    output.append(
                        f"#### {method_name}{self._format_function_signature(method_info)}\n"
                    )
                    if method_info.get("docstring"):
                        output.append(f"\n{method_info['docstring']}\n")
        return "\n".join(output)

    def _format_class(self, class_name: str, class_info: dict) -> str:
        """Format class documentation with proper cross-references"""
        class_doc = class_info.get("doc", "No class documentation")
        methods = "\n".join(
            self._format_function(method_name, method_info)
            for method_name, method_info in class_info.get("methods", {}).items()
        )
        return f"## [[{class_name}]]\n\n{class_doc}\n\n{methods}\n"

    def _format_function(self, func_name: str, func_info: dict) -> str:
        """Format function with AST node handling"""
        try:
            args = func_info.get("args", [])
            # Validate arguments type before processing
            if not isinstance(args, (ast.arguments, list)):
                raise TypeError(f"Invalid arguments type: {type(args).__name__}")

            returns = func_info.get("returns", "None")
            doc = func_info.get("doc", "No docstring available")

            arg_list = []
            if isinstance(args, ast.arguments):
                # Handle positional arguments with defaults
                defaults = [None] * (len(args.args) - len(args.defaults)) + list(
                    args.defaults
                )
                for arg, default in zip(args.args, defaults):
                    arg_name = arg.arg
                    arg_type = ast.unparse(arg.annotation) if arg.annotation else "Any"
                    default_str = f" = {ast.unparse(default)}" if default else ""
                    arg_list.append(f"{arg_name}: {arg_type}{default_str}")

                # Handle *args and **kwargs
                if args.vararg:
                    arg_list.append(f"*{args.vararg.arg}")
                if args.kwarg:
                    arg_list.append(f"**{args.kwarg.arg}")

                arg_str = ", ".join(arg_list)
            elif isinstance(args, list):
                arg_str = ", ".join(args)
            else:
                arg_str = "..."

            return_type = (
                ast.unparse(returns) if isinstance(returns, ast.AST) else returns
            )
            return (
                f"### `{func_name}({arg_str}) -> {return_type}`\n\n"
                f"{doc}\n\n"
                "```{{eval-auto}}\n# --8<-- [start:example]\n\n# --8<-- [end:example]\n```\n"
            )
        except Exception as e:
            return f"### `{func_name}()`\n\n*Error: {str(e)[:100]}*\n"

    def _handle_import_from(self, node: ast.ImportFrom) -> None:
        if node.module and any(self._is_public_name(name.name) for name in node.names):
            self._add_import_relationship(module=node.module, level=node.level or 0)

    def _format_attribute(self, node: ast.Attribute) -> str:
        return (
            f"`{self._get_attr_source(node)}` "
            f"(from {self._get_module_name(node.value)})"
        )

    def _format_role_section(self, module: dict) -> str:
        """Generate role and architecture section"""
        role = module.get("role", "General purpose module")
        layer = module.get("architecture_layer", "Not specified")
        return f"\n- **Role**: {role}\n- **Architecture Layer**: {layer}\n"


def generate_docs(package_info: dict, output_path: Path) -> None:
    writer = MystWriter()
    writer.generate(package_info, output_path)
