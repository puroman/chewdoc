# Dependency analysis and relationship mapping
from collections import defaultdict

def analyze_relationships(modules: list, package_name: str) -> dict:
    """Analyze module relationships and dependencies."""
    relationships = defaultdict(list)
    
    for module in modules:
        module_name = module["name"]
        # Track internal dependencies
        relationships[module_name].extend(
            dep for dep in module.get("internal_deps", [])
            if dep.startswith(package_name)
        )
        
        # Track external imports
        for imp in module.get("imports", []):
            if imp["type"] == "external":
                relationships[module_name].append(f"external:{imp['source']}")
            elif imp["type"] == "stdlib":
                relationships[module_name].append(f"stdlib:{imp['name']}")
    
    return {
        "dependency_graph": dict(relationships),
        "external_deps": list({
            imp["source"] for module in modules
            for imp in module.get("imports", [])
            if imp["type"] == "external"
        })
    } 