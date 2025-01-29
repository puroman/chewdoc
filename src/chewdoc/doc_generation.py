from pathlib import Path
import logging
from typing import Any, Dict
from .formatters.myst_writer import MystWriter

logger = logging.getLogger(__name__)

def generate_docs(package_info: Dict[str, Any], output_dir: Path, verbose: bool = False) -> None:
    """Generate documentation files using configured formatter."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if verbose:
        logger.info(f"📄 Generating docs in {output_dir}")
    
    writer = MystWriter()
    
    for module in package_info.get("modules", []):
        module_name = module["name"]
        output_path = output_dir / f"{module_name}.md"
        content = writer.format_module(module, package_info)
        output_path.write_text(content)
        
    if verbose:
        logger.info(f"✅ Generated {len(package_info.get('modules', []))} module files") 