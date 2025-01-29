"""
Configuration handling for chewdoc documentation generator
"""

from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from chewdoc.constants import (  # Updated imports
    DEFAULT_EXCLUSIONS,
    TEMPLATE_VERSION,
    TYPE_ALIASES,
)
import tomli


class ChewdocConfig(BaseModel):
    """Main configuration model for chewdoc"""

    exclude_patterns: List[str] = Field(
        default=DEFAULT_EXCLUSIONS,
        description="File patterns to exclude from processing"
    )
    template_version: str = Field(
        TEMPLATE_VERSION, description="Version identifier for documentation templates"
    )
    known_types: Dict[str, str] = Field(
        default=TYPE_ALIASES,
        description="Type aliases for simplifying complex annotations"
    )
    output_format: str = Field(default="myst", description="Output format (myst/markdown)")
    template_dir: Optional[Path] = Field(default=None, description="Custom template directory")
    enable_cross_references: bool = Field(default=True, description="Generate cross-module links")
    max_example_lines: int = Field(default=10, ge=1, description="Max lines in usage examples")

    model_config = ConfigDict(extra="forbid")


def validate_examples(examples: list) -> list:
    """Ensure examples have correct structure."""
    validated = []
    for ex in examples:
        if isinstance(ex, dict) and "code" in ex:
            validated.append(ex)
        elif isinstance(ex, str):
            validated.append({"code": ex, "output": ""})
    return validated


def load_config(path: Optional[Path] = None) -> ChewdocConfig:
    """Load configuration from file or return defaults"""
    if path and path.exists():
        with open(path, "rb") as f:
            config_data = tomli.load(f).get("tool", {}).get("chewdoc", {})
            if 'examples' in config_data:
                config_data['examples'] = validate_examples(config_data['examples'])
            return ChewdocConfig(**config_data)
    return ChewdocConfig()
