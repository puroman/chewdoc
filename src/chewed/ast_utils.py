# AST processing utilities
import astroid
import logging
from typing import Dict, Any, Optional, List
from astroid import nodes

logger = logging.getLogger(__name__)


def extract_docstrings(node: nodes.Module) -> Dict[str, str]:
    """Extract docstrings from AST nodes."""
    logger.info("Extracting docstrings from AST nodes")
    docs = {}
    
    for child in node.nodes_of_class((nodes.Module, nodes.ClassDef, nodes.FunctionDef)):
        if child.doc:
            name = getattr(child, 'name', 'module')
            logger.debug(f"Found docstring for {name}")
            docs[name] = child.doc.strip()
            
    logger.debug(f"Extracted {len(docs)} docstrings")
    return docs


def extract_type_info(node: nodes.Module, config: Any) -> Dict[str, Any]:
    """Extract type annotations from AST nodes."""
    logger.info("Extracting type annotations from AST nodes")
    type_info = {}
    
    for child in node.nodes_of_class((nodes.AnnAssign, nodes.FunctionDef)):
        if isinstance(child, nodes.AnnAssign):
            if isinstance(child.target, nodes.Name):
                logger.debug(f"Found type annotation for variable {child.target.name}")
                type_info[child.target.name] = child.annotation.as_string()
                
        elif isinstance(child, nodes.FunctionDef):
            logger.debug(f"Processing function {child.name}")
            returns = child.returns.as_string() if child.returns else None
            args = [
                arg.annotation.as_string() 
                for arg in child.args.args 
                if arg.annotation
            ]
            if returns or args:
                logger.debug(f"Found type info for function {child.name}")
                type_info[child.name] = {
                    "return_type": returns,
                    "arg_types": args
                }
                
    logger.debug(f"Extracted type info for {len(type_info)} nodes")
    return type_info


def validate_ast(node: nodes.Module) -> None:
    """Validate AST structure with enhanced assignment checking"""
    logger.info("Validating AST structure")
    
    for child in node.nodes_of_class(nodes.Assign):
        logger.debug(f"Checking assignment at line {getattr(child, 'lineno', 'unknown')}")
        
        for target in child.targets:
            if not isinstance(target, (nodes.Name, nodes.Attribute, nodes.Subscript)):
                line = getattr(target, 'lineno', 'unknown')
                logger.error(f"Invalid assignment target found at line {line}")
                raise ValueError(
                    f"Invalid assignment target at line {line}: {target.as_string()}"
                )

        if isinstance(child, nodes.Dict):
            if len(child.items) != len(set(k.value for k, _ in child.items)):
                line = getattr(child, 'lineno', 'unknown')
                logger.error(f"Duplicate dictionary keys found at line {line}")
                raise ValueError(
                    f"Invalid Dict at line {line} - duplicate keys found"
                )
