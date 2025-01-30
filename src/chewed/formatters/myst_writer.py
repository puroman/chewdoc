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

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler with formatting
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class MystWriter:
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self._init_templates()

    def _init_templates(self):
        """Initialize documentation templates"""
        self.module_template = (
            self.config.get("module_template") 
            or """# {module_name}

{description}

## Functions
{% for func in functions %}
### `{func.name}`
**Parameters**: {func.params}
**Returns**: {func.returns}
{% endfor %}

{examples}
"""
        )

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize module name for filename"""
        return name.replace(".", "_").lower()

    def _process_examples(self, examples: List[Dict]) -> List[Dict]:
        """Process and validate examples"""
        self.logger.debug(f"Processing {len(examples)} examples")
        valid_examples = []
        for example in examples:
            if isinstance(example, dict):
                if "code" not in example and "content" not in example:
                    self.logger.warning(
                        "Skipping example: Missing 'code'/'content' field"
                    )
                    continue
                valid_examples.append(example)
            elif isinstance(example, str):
                valid_examples.append({"code": example})
        self.logger.debug(f"Processed {len(valid_examples)} valid examples")
        return valid_examples

    def _format_module(self, module: dict) -> str:
        """Format module data into Myst content"""
        self.logger.info(f"Formatting module: {module.get('name')}")
        
        # Basic module info
        content = [
            f"# {module.get('name', 'Unnamed Module')}",
            f"\n**Source Path**: `{module.get('path', 'unknown')}`\n"
        ]
        
        # Module description/docstring
        if docstrings := module.get('docstrings', {}):
            if module_doc := docstrings.get('Module:module', ''):
                content.append(f"\n{module_doc}\n")
        
        # Functions section
        if functions := module.get('functions', {}):
            content.append("\n## Functions\n")
            for func_name, func_info in functions.items():
                content.append(f"### `{func_name}`\n")
                
                # Function signature
                if args := func_info.get('args', []):
                    args_str = ", ".join(
                        f"{arg['name']}: {arg.get('annotation', 'Any')}"
                        for arg in args
                    )
                    content.append(f"```python\ndef {func_name}({args_str})"
                                 f" -> {func_info.get('returns', 'None')}\n```\n")
                
                # Function docstring
                if doc := func_info.get('docstring'):
                    content.append(f"{doc}\n")
        
        # Classes section
        if classes := module.get('classes', {}):
            content.append("\n## Classes\n")
            for class_name, class_info in classes.items():
                content.append(f"### {class_name}\n")
                
                # Class docstring
                if doc := class_info.get('docstring'):
                    content.append(f"{doc}\n")
                
                # Class methods
                if methods := class_info.get('methods', {}):
                    for method_name, method_info in methods.items():
                        content.append(f"#### `{method_name}`\n")
                        if doc := method_info.get('docstring'):
                            content.append(f"{doc}\n")
                        if args := method_info.get('args'):
                            content.append(f"**Parameters**: {', '.join(args)}\n")
                        if returns := method_info.get('returns'):
                            content.append(f"**Returns**: `{returns}`\n")
        
        return "\n".join(content)

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

        except Exception as e:
            self.logger.error(f"Documentation generation failed: {str(e)}")
            raise

    def _format_package_index(self, package_data: Dict[str, Any]) -> str:
        """Generate main package index with module links and toctree"""
        package_name = package_data.get(
            "name", package_data.get("package", "Unknown Package")
        )
        self.logger.debug(f"Formatting package index for {package_name}")

        content = [
            f"# {package_name} Documentation\n",
            "```{toctree}",
            ":maxdepth: 2",
            ":caption: Contents:",
            "",  # Empty line after caption
        ]

        # Add module entries to toctree
        modules = package_data.get("modules", [])
        self.logger.debug(f"Adding {len(modules)} modules to toctree")
        for mod in modules:
            module_name = mod.get("name", "") if isinstance(mod, dict) else str(mod)
            if module_name:
                sanitized_name = self._sanitize_filename(module_name)
                content.append(sanitized_name)

        content.extend(
            [
                "```\n",
                "## Package Overview",
                self._format_metadata(package_data),
                "\n## Modules\n",
            ]
        )

        # Add module links
        self.logger.debug("Adding module links")
        for mod in modules:
            module_name = mod.get("name", "") if isinstance(mod, dict) else str(mod)
            if module_name:
                sanitized_name = self._sanitize_filename(module_name)
                content.append(f"- [{module_name}]({sanitized_name}.md)")

        return "\n".join(content)

    def _format_metadata(self, package_data: Dict[str, Any]) -> str:
        """Format package metadata section"""
        self.logger.debug("Formatting package metadata")
        metadata = {
            "Name": package_data.get("name", package_data.get("package", "Unknown")),
            "Version": package_data.get("version", "0.0.0"),
            "Author": package_data.get("author", "Unknown Author"),
            "License": package_data.get("license", "Not specified"),
            "Interface": package_data.get("interface", "Not specified"),
        }

        return "\n".join(
            [
                "\n### Package Overview",
                *[f"**{key}**: {value}" for key, value in metadata.items()],
                "\n",
            ]
        )

    def _format_role(self, module: dict) -> str:
        """Format module role description"""
        role = module.get("role", "General purpose module")
        self.logger.debug(f"Formatting role: {role}")
        return f"- **Role**: {role}"

    def _format_architecture_layer(self, module: dict) -> str:
        """Format module architecture layer information"""
        layer = module.get("layer", "Not specified")
        self.logger.debug(f"Formatting architecture layer: {layer}")
        return f"- **Architecture Layer**: {layer}"

    def _format_dependencies(self, dependencies: list) -> str:
        """Format module dependencies as Mermaid graph"""
        self.logger.debug(f"Formatting {len(dependencies) if dependencies else 0} dependencies")
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
        self.logger.debug(f"Formatting {len(modules)} modules for index")
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
                    error_msg = f"Invalid arguments: {str(args)[:50]}"
                    self.logger.warning(error_msg)
                    return f"()  # {error_msg}"

                return format_function_signature(
                    ast.arguments(
                        args=[ast.arg(arg=str(arg)) for arg in args_list],
                        defaults=args.get("defaults", []),
                    ),
                    returns,
                    config,
                )

            self.logger.warning("Unable to parse arguments")
            return "()  # Unable to parse arguments"

        except Exception as e:
            error_msg = f"Error formatting signature: {str(e)[:100]}"
            self.logger.error(error_msg, exc_info=True)
            return f"()  # {error_msg}"

    def _validate_example(self, example: Any) -> Optional[Dict[str, str]]:
        """Robust example validation with detailed logging"""
        self.logger.debug(f"Validating example of type {type(example).__name__}")
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
        self.logger.debug(f"Formatting {len(examples)} usage examples")
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
        self.logger.debug("Extracting docstrings")
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
                    self.logger.warning(f"Error extracting docstring: {str(e)}")
                    continue
        return docs

    def _get_module_description(self, module: dict) -> str:
        """Extract module description from docstrings"""
        self.logger.debug("Getting module description")
        if "docstrings" in module and "module:1" in module["docstrings"]:
            return module["docstrings"]["module:1"]
        return infer_responsibilities(module)

    def _format_classes(self, classes: dict) -> str:
        self.logger.debug(f"Formatting {len(classes)} classes")
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
        self.logger.debug(f"Formatting class: {class_name}")
        class_doc = class_info.get("doc", "No class documentation")
        methods = "\n".join(
            self._format_function(method_name, method_info)
            for method_name, method_info in class_info.get("methods", {}).items()
        )
        return f"## [[{class_name}]]\n\n{class_doc}\n\n{methods}\n"

    def _format_function(self, func_name: str, func_info: dict) -> str:
        """Format function with AST node handling"""
        self.logger.debug(f"Formatting function: {func_name}")
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
            error_msg = f"Error formatting function {func_name}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
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
        self.logger.debug(f"Formatting role section - Role: {role}, Layer: {layer}")
        return f"\n- **Role**: {role}\n- **Architecture Layer**: {layer}\n"

    # Alias for backward compatibility with tests
    _format_module_content = _format_module


def generate_docs(package_info: dict, output_path: Path) -> None:
    logger.info("Starting documentation generation")
    writer = MystWriter()
    writer.generate(package_info, output_path)
    logger.info("Documentation generation completed")
