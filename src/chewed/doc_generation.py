from pathlib import Path
import logging
from typing import Any, Dict, List, Union
from .formatters.myst_writer import MystWriter
from .types import ModuleInfo
from chewed.module_processor import process_modules
from .stats import StatsCollector

logger = logging.getLogger(__name__)


def generate_docs(package_info: Dict[str, Any], output_dir: Path, verbose: bool = False) -> None:
    """
    Generate documentation for a package with robust error handling.
    
    Args:
        package_info (Dict[str, Any]): Package analysis results
        output_dir (Path): Directory to write documentation
        verbose (bool, optional): Enable verbose logging. Defaults to False.
    """
    logger.info(f"Starting documentation generation for output directory: {output_dir}")
    try:
        # Ensure output directory exists
        logger.debug(f"Creating output directory: {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize the Myst writer with config
        writer = MystWriter(config=package_info.get("config", {}))
        
        # Generate main documentation structure
        logger.info("Generating documentation structure")
        writer.generate(package_info, output_dir)

        # Create supplemental index file
        index_path = output_dir / "index.md"
        package_name = package_info.get('package', 'Unnamed Package')
        
        with open(index_path, 'w') as f:
            f.write(f"# {package_name} Documentation\n\n")
            
            # Add basic metadata
            if metadata := package_info.get('metadata'):
                logger.debug("Adding metadata section")
                f.write("## Package Metadata\n")
                for key, value in metadata.items():
                    logger.debug(f"Writing metadata: {key}={value}")
                    f.write(f"- **{key}**: {value}\n")
            
            # Module list with links
            if modules := package_info.get('modules'):
                logger.debug(f"Adding modules section with {len(modules)} modules")
                f.write("\n## Modules\n")
                for module in modules:
                    module_name = module.get('name')
                    if module_name:
                        filename = writer._sanitize_filename(module_name) + ".md"
                        logger.debug(f"Adding module: {module_name}")
                        f.write(f"- [{module_name}]({filename})\n")
            
            # Add relationships if available
            relationships = package_info.get('relationships', {})
            if relationships:
                logger.debug("Adding relationships section")
                f.write("\n## Dependencies\n")
                
                # Dependency graph
                dep_graph = relationships.get('dependency_graph', {})
                if dep_graph:
                    logger.debug("Writing internal dependencies")
                    f.write("### Internal Dependencies\n")
                    for module, deps in dep_graph.items():
                        logger.debug(f"Writing dependencies for {module}")
                        f.write(f"- **{module}**: {', '.join(deps) or 'No dependencies'}\n")
                
                # External dependencies
                external_deps = relationships.get('external_deps', [])
                if external_deps:
                    logger.debug(f"Writing {len(external_deps)} external dependencies")
                    f.write("\n### External Dependencies\n")
                    for dep in external_deps:
                        logger.debug(f"Adding external dependency: {dep}")
                        f.write(f"- {dep}\n")

        logger.info(f"Documentation generated successfully in {output_dir}")
        if verbose:
            logger.info(f"Documentation written to {output_dir}")

    except Exception as e:
        logger.error(f"Documentation generation failed: {str(e)}")
        if verbose:
            logger.exception("Detailed error:")
        
        # Fallback: create minimal documentation
        logger.warning("Attempting to create fallback documentation")
        with open(output_dir / "index.md", 'w') as f:
            f.write(f"# Documentation Generation Failed\n\n")
            f.write(f"Error: {str(e)}\n")
