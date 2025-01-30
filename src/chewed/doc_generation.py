from pathlib import Path
import logging
from typing import Any, Dict, List, Union
from .formatters.myst_writer import MystWriter
from .types import ModuleInfo
from chewed.module_processor import process_modules
from .stats import StatsCollector

logger = logging.getLogger(__name__)


def generate_docs(package_info: dict, output_path: Path) -> None:
    """Generate documentation for a package."""
    logger.info("Starting documentation generation...")
    try:
        # Ensure output directory exists
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate documentation using MystWriter
        writer = MystWriter()
        writer.generate(package_info, output_path)

        logger.info(f"Documentation generated successfully in {output_path}")
    except Exception as e:
        logger.error(f"Failed to generate documentation: {str(e)}")
        raise
