# Dependency analysis and relationship mapping
from collections import defaultdict
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def analyze_relationships(modules: List[Dict[str, Any]], package_name: str) -> Dict[str, Any]:
    """Analyze module relationships and dependencies."""
    logger.info(f"Analyzing relationships for package: {package_name}")
    relationships = defaultdict(list)

    for module in modules:
        # Safely extract module name, using a fallback
        module_name = module.get('name', f"unnamed_module_{id(module)}")
        logger.debug(f"Processing module: {module_name}")
        
        # Track internal dependencies
        internal_deps = module.get('internal_deps', [])
        filtered_deps = [dep for dep in internal_deps if dep.startswith(package_name)]
        relationships[module_name].extend(filtered_deps)
        logger.debug(f"Found {len(filtered_deps)} internal dependencies for {module_name}")

        # Track external imports
        imports = module.get('imports', [])
        logger.debug(f"Processing {len(imports)} imports for {module_name}")
        
        for imp in imports:
            if not isinstance(imp, dict):
                logger.warning(f"Skipping invalid import format in {module_name}")
                continue
            
            import_type = imp.get('type')
            import_source = imp.get('source', imp.get('full_path', 'unknown'))
            
            if import_type == 'external':
                logger.debug(f"Found external dependency: {import_source}")
                relationships[module_name].append(f"external:{import_source}")
            elif import_type == 'stdlib':
                logger.debug(f"Found stdlib dependency: {import_source}")
                relationships[module_name].append(f"stdlib:{import_source}")

    logger.info(f"Completed relationship analysis for {len(modules)} modules")
    external_deps = {
        imp.get('source', imp.get('full_path', 'unknown'))
        for module in modules
        for imp in module.get('imports', [])
        if isinstance(imp, dict) and imp.get('type') == 'external'
    }
    logger.debug(f"Found {len(external_deps)} unique external dependencies")

    return {
        "dependency_graph": dict(relationships),
        "external_deps": list(external_deps),
    }
