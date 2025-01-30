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
        self.logger = logging.getLogger(__name__)
        self.config = config or chewedConfig()

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize module name for file system"""
        # Replace dots and slashes with underscores
        sanitized = name.replace(".", "_").replace("/", "_")
        # Remove any other invalid characters
        return re.sub(r'[^\w\-_.]', '_', sanitized)

    def _process_examples(self, examples: List[Dict]) -> List[Dict]:
        """Process and validate examples"""
        valid_examples = []
        for example in examples:
            if isinstance(example, dict):
                if 'code' not in example and 'content' not in example:
                    self.logger.warning("Skipping example: Missing 'code'/'content' field")
                    continue
                valid_examples.append(example)
            elif isinstance(example, str):
                valid_examples.append({"code": example})
        return valid_examples

    def generate(self, package_info: Dict, output_dir: Path) -> None:
        """Generate documentation with improved path handling and logging"""
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Generating documentation in {output_dir}")

            # Generate module documentation
            for module in package_info.get("modules", []):
                module_name = module.get("name", "")
                if not module_name:
                    self.logger.warning("Skipping module with no name")
                    continue

                # Sanitize filename
                filename = self._sanitize_filename(module_name) + ".md"
                file_path = output_dir / filename

                try:
                    # Process examples if present
                    if "examples" in module:
                        module["examples"] = self._process_examples(module["examples"])

                    # Generate content and write file
                    content = self._format_module(module)
                    file_path.write_text(content)
                    self.logger.debug(f"Generated {filename}")
                except Exception as e:
                    self.logger.error(f"Error generating {filename}: {str(e)}")
                    # Continue with other modules even if one fails
                    continue

            # Generate index
            try:
                index_content = self._format_package_index(package_info)
                index_path = output_dir / "index.md"
                index_path.write_text(index_content)
                self.logger.debug("Generated index.md")
            except Exception as e:
                self.logger.error(f"Error generating index.md: {str(e)}")
                raise

        except Exception as e:
            self.logger.error(f"Documentation generation failed: {str(e)}")
            raise

    def _format_package_index(self, package_data: Dict[str, Any]) -> str:
        """Generate main package index with module links and toctree"""
        package_name = package_data.get('name', package_data.get('package', 'Unknown Package'))
        
        content = [
            f"# {package_name} Documentation\n",
            "```{toctree}",
            ":maxdepth: 2",
            ":caption: Contents:",
            ""  # Empty line after caption
        ]

        # Add module entries to toctree
        for mod in package_data.get("modules", []):
            module_name = mod.get("name", "") if isinstance(mod, dict) else str(mod)
            if module_name:
                sanitized_name = self._sanitize_filename(module_name)
                content.append(sanitized_name)

        content.extend([
            "```\n",
            "## Package Overview",
            self._format_metadata(package_data),
            "\n## Modules\n"
        ])

        # Add module links
        for mod in package_data.get("modules", []):
            module_name = mod.get("name", "") if isinstance(mod, dict) else str(mod)
            if module_name:
                sanitized_name = self._sanitize_filename(module_name)
                content.append(f"- [{module_name}]({sanitized_name}.md)")

        return "\n".join(content)

    def _format_module(self, module: dict) -> str:
        """Format module content with proper headers and sections"""
        try:
            module_name = module.get("name", "unknown")
            content = [
                f"# Module: {module_name}\n",
                module.get("docstring", module.get("docstrings", {}).get("module", "No module documentation available")),
                "\n"
            ]

            # Add examples if present
            if examples := module.get("examples", []):
                content.extend([
                    "## Examples\n",
                    self._format_usage_examples(examples),
                    "\n"
                ])

            # Add type information only if there's actual content
            if type_info := module.get("type_info", {}):
                has_complex_content = False
                has_variables = False
                sections = []

                # Add variables only if they have actual values
                if variables := type_info.get("variables"):
                    # Filter out empty or None values
                    valid_vars = {
                        name: value for name, value in variables.items() 
                        if value is not None and (
                            not isinstance(value, dict) or 
                            value.get("value") is not None
                        )
                    }
                    if valid_vars:
                        has_variables = True
                        sections.extend([
                            "### Variables\n",
                            *[f"- `{name}`: {self._format_variable_value(value)}" for name, value in valid_vars.items()],
                            "\n"
                        ])

                # Add classes
                if classes := type_info.get("classes"):
                    has_complex_content = True
                    for class_name, class_info in classes.items():
                        sections.append(self._format_class(class_name, class_info))

                # Add functions
                if functions := type_info.get("functions"):
                    has_complex_content = True
                    sections.append("### Functions\n")
                    for func_name, func_info in functions.items():
                        sections.append(self._format_function(func_name, func_info))

                # Only add API Reference section if there's complex content
                # For minimal modules with only variables, add them directly
                if has_complex_content:
                    content.extend(["## API Reference\n"] + sections)
                elif has_variables:
                    content.extend(sections)

            # Add role section
            content.append(self._format_role_section(module))

            return "\n".join(content)
        except Exception as e:
            self.logger.error(f"Error formatting module {module.get('name', 'unknown')}: {str(e)}")
            return f"# Module: {module.get('name', 'unknown')}\n\nError generating documentation: {str(e)}"

    def _format_variable_value(self, value: Any) -> str:
        """Format variable value for documentation"""
        if isinstance(value, dict) and "value" in value:
            return str(value["value"])
        return str(value)

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
        """Format package metadata section"""
        metadata = {
            "Name": package_data.get('name', package_data.get('package', 'Unknown')),
            "Version": package_data.get('version', '0.0.0'),
            "Author": package_data.get('author', 'Unknown Author'),
            "License": package_data.get('license', 'Not specified'),
            "Interface": package_data.get('interface', 'Not specified')
        }
        
        return "\n".join([
            "\n### Package Overview",
            *[f"**{key}**: {value}" for key, value in metadata.items()],
            "\n"
        ])

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

    # Alias for backward compatibility with tests
    _format_module_content = _format_module


def generate_docs(package_info: dict, output_path: Path) -> None:
    writer = MystWriter()
    writer.generate(package_info, output_path)
