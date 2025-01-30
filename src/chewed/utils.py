import ast
from chewed.config import chewedConfig
from typing import Any, List, Tuple, Union, Optional, Dict
from pathlib import Path
import logging
import re
import os

logger = logging.getLogger(__name__)


def get_annotation(node: ast.AST, config: chewedConfig) -> str:
    """Simplify type annotations for documentation"""
    logger.debug("Simplifying type annotation")
    annotation = ast.unparse(node).strip()
    logger.debug(f"Raw annotation: {annotation}")
    # Replace full module paths with base names
    simplified = re.sub(r"\b(\w+\.)+(\w+)\b", r"\2", annotation)
    logger.debug(f"Simplified annotation: {simplified}")
    return simplified


def infer_responsibilities(module: dict) -> str:
    """Generate module responsibility description based on contents"""
    logger.debug("Inferring module responsibilities")

    def safe_get_names(items, key="name") -> list:
        """Safely extract names from mixed list/dict structures"""
        logger.debug(f"Extracting names with key '{key}' from {type(items)}")
        if isinstance(items, dict):
            names = [v.get(key, "") for v in items.values() if v.get(key)]
        elif isinstance(items, list):
            names = [item.get(key, "") for item in items if item.get(key)]
        else:
            names = []
        logger.debug(f"Extracted names: {names}")
        return names

    responsibilities = []

    # Handle classes
    if classes := module.get("classes"):
        logger.debug("Processing classes")
        class_names = safe_get_names(classes)
        class_list = class_names[:3]
        resp = "Defines core classes: " + ", ".join(class_list)
        if len(class_names) > 3:
            resp += f" (+{len(class_names)-3} more)"
        logger.debug(f"Added class responsibility: {resp}")
        responsibilities.append(resp)

    # Handle functions
    if functions := module.get("functions"):
        logger.debug("Processing functions")
        func_names = safe_get_names(functions)
        func_list = func_names[:3]
        resp = "Provides key functions: " + ", ".join(func_list)
        if len(func_names) > 3:
            resp += f" (+{len(func_names)-3} more)"
        logger.debug(f"Added function responsibility: {resp}")
        responsibilities.append(resp)

    # Handle constants
    if constants := module.get("constants"):
        logger.debug("Processing constants")
        const_names = safe_get_names(constants)
        const_list = const_names[:3]
        resp = "Contains constants: " + ", ".join(const_list)
        if len(const_names) > 3:
            resp += f" (+{len(const_names)-3} more)"
        logger.debug(f"Added constant responsibility: {resp}")
        responsibilities.append(resp)

    if not responsibilities:
        logger.info("No specific responsibilities found")
        return "General utility module with mixed responsibilities"

    result = "\n- ".join([""] + responsibilities)
    logger.debug(f"Final responsibilities: {result}")
    return result


def validate_ast(node: ast.AST) -> None:
    """Validate AST structure with enhanced assignment checking"""
    logger.debug("Starting AST validation")
    for child in ast.walk(node):
        if isinstance(child, ast.Assign):
            logger.debug("Validating assignment node")
            for target in child.targets:
                if not isinstance(target, (ast.Name, ast.Attribute, ast.Subscript)):
                    line = getattr(target, "lineno", "unknown")
                    logger.error(f"Invalid assignment target found at line {line}")
                    raise ValueError(
                        f"Invalid assignment target at line {line}: {ast.dump(target)}"
                    )

        if isinstance(child, ast.Dict):
            logger.debug("Validating dictionary node")
            if len(child.keys) != len(child.values):
                line = getattr(child, "lineno", "unknown")
                logger.error(f"Dict key/value mismatch at line {line}")
                raise ValueError(
                    f"Invalid Dict at line {line} - key/value count mismatch "
                    f"({len(child.keys)} keys vs {len(child.values)} values)"
                )
    logger.info("AST validation completed successfully")


def find_usage_examples(node: ast.AST) -> list:
    """Placeholder example finder (implement your logic here)"""
    logger.debug("Example finder called (not implemented)")
    return []  # TODO: Add actual example extraction logic


def format_function_signature(
    args: ast.arguments, returns: Optional[ast.AST], config: chewedConfig
) -> str:
    """Format function signature with proper argument handling"""
    logger.debug("Formatting function signature")
    args_list = []
    defaults = [None] * (len(args.args) - len(args.defaults)) + list(args.defaults)

    for arg, default in zip(args.args, defaults):
        logger.debug(f"Processing argument: {arg.arg}")
        arg_str = arg.arg
        if arg.annotation:
            arg_str += f": {get_annotation(arg.annotation, config)}"
        if default:
            default_src = ast.unparse(default).strip()
            arg_str += f" = {default_src}"
        args_list.append(arg_str)

    return_str = ""
    if returns:
        logger.debug("Processing return annotation")
        return_str = f" -> {get_annotation(returns, config)}"

    result = f"({', '.join(args_list)}){return_str}"
    logger.debug(f"Final signature: {result}")
    return result


def _find_imports(node: ast.AST) -> list:
    """Extract import statements from AST"""
    logger.debug("Starting import extraction")
    imports = []

    class ImportVisitor(ast.NodeVisitor):
        def visit_Import(self, node):
            logger.debug("Processing Import node")
            for alias in node.names:
                logger.debug(f"Found import: {alias.name}")
                imports.append(alias.name)

        def visit_ImportFrom(self, node):
            logger.debug("Processing ImportFrom node")
            module = node.module or ""
            for alias in node.names:
                import_name = f"{module}.{alias.name}" if module else alias.name
                logger.debug(f"Found import from: {import_name}")
                imports.append(import_name)

    ImportVisitor().visit(node)
    logger.debug(f"Found {len(imports)} imports")
    return imports


def extract_constant_values(node: ast.AST) -> List[Tuple[str, str]]:
    """Extract module-level constants with ALL_CAPS names"""
    logger.debug("Starting constant extraction")
    constants = []
    for stmt in node.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    value = ast.unparse(stmt.value).strip()
                    logger.debug(f"Found constant: {target.id} = {value}")
                    constants.append((target.id, value))
    logger.debug(f"Extracted {len(constants)} constants")
    return constants


def safe_write(
    path: Path, content: str, mode: str = "w", overwrite: bool = False
) -> None:
    """Atomic file write with directory creation"""
    logger.debug(f"Attempting to write to {path}")
    if path.exists() and not overwrite:
        logger.error(f"Cannot write: {path} exists and overwrite=False")
        raise FileExistsError(f"File already exists: {path}")

    logger.debug("Creating parent directories if needed")
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Writing content in mode '{mode}'")
    with open(path, mode) as f:
        f.write(content)
    logger.info(f"Successfully wrote to {path}")


def relative_path(from_path: Path, to_path: Path) -> Path:
    logger.debug(f"Computing relative path from {from_path} to {to_path}")
    result = Path(
        os.path.relpath(
            str(to_path), str(from_path.parent if from_path.is_file() else from_path)
        )
    ).with_suffix("")
    logger.debug(f"Relative path result: {result}")
    return result


def _validate_examples(self, raw_examples: List) -> List[Dict]:
    logger.debug(f"Validating {len(raw_examples)} examples")
    valid = []
    for idx, ex in enumerate(raw_examples):
        logger.debug(f"Processing example {idx}")
        if isinstance(ex, str):
            logger.debug("Found string example")
            valid.append({"code": ex, "output": None})
        elif isinstance(ex, dict):
            if "content" in ex:  # Legacy format
                logger.debug("Found legacy format example")
                valid.append({"code": ex["content"], "output": ex.get("result")})
            elif "code" in ex:
                logger.debug("Found standard format example")
                valid.append({"code": str(ex["code"]), "output": ex.get("output")})
            else:
                logger.warning(f"Skipping invalid example at index {idx}")
        else:
            logger.warning(f"Skipping invalid example of type {type(ex).__name__}")
    logger.info(f"Validated {len(valid)} examples")
    return valid
