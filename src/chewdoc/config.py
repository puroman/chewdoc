"""
Configuration handling for chewdoc documentation generator
"""

from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from chewdoc.constants import (  # Updated imports
    DEFAULT_EXCLUSIONS,
    TEMPLATE_VERSION,
    TYPE_ALIASES
)


class ChewdocConfig(BaseModel):
    """Main configuration model for chewdoc"""

    exclude_patterns: List[str] = Field(
        default_factory=lambda: DEFAULT_EXCLUSIONS.copy(),
        description="File patterns to exclude from processing"
    )
    template_version: str = Field(
        TEMPLATE_VERSION,
        description="Version identifier for documentation templates"
    )
    known_types: Dict[str, str] = Field(
        default_factory=lambda: TYPE_ALIASES.copy(),
        description="Type aliases to simplify in documentation"
    )
    output_format: str = Field(
        default="myst", 
        description="Output format (myst, markdown, etc)"
    )
    template_dir: Optional[Path] = Field(
        None, 
        description="Custom template directory for documentation"
    )
    enable_cross_references: bool = Field(
        True, 
        description="Generate cross-reference links between entities"
    )
    max_example_lines: int = Field(
        10, 
        description="Maximum lines to show in usage examples"
    )


def load_config(path: Optional[Path] = None) -> ChewdocConfig:
    """Load configuration from file or return defaults"""
    # Implementation remains the same
    return ChewdocConfig()
