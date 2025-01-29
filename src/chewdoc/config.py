"""
Configuration handling for chewdoc documentation generator
"""

from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict, ValidationError
from chewdoc.constants import (  # Updated imports
    DEFAULT_EXCLUSIONS,
    TEMPLATE_VERSION,
    TYPE_ALIASES,
)
import tomli
import logging

logger = logging.getLogger(__name__)


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


class ExampleSchema(BaseModel):
    code: str
    output: str = ""


def validate_examples(examples: list) -> list:
    """Validate examples with detailed error reporting."""
    validated = []
    for idx, ex in enumerate(examples, 1):
        try:
            # Handle string examples
            if isinstance(ex, str):
                validated.append({
                    "type": "doctest",
                    "code": ex,
                    "output": ""
                })
                continue
                
            # Require dictionary format
            if not isinstance(ex, dict):
                raise TypeError(f"Example #{idx} is {type(ex).__name__}, expected dict")
                
            # Check required fields
            if "code" not in ex and "content" not in ex:
                raise ValueError(f"Example #{idx} missing code/content")
                
            validated.append({
                "type": ex.get("type", "doctest"),
                "code": str(ex.get("code", ex.get("content", ""))),
                "output": str(ex.get("output", ex.get("result", "")))
            })
            
        except (TypeError, ValueError) as e:
            logger.error(f"Config validation failed for example #{idx}: {e}")
            
    return validated


def load_config(path: Optional[Path] = None) -> ChewdocConfig:
    """Load configuration from file or return defaults"""
    if path and path.exists():
        with open(path, "rb") as f:
            config_data = tomli.load(f).get("tool", {}).get("chewdoc", {})
            
            # Add type enforcement for examples
            raw_examples = config_data.get('examples', [])
            if not isinstance(raw_examples, list):
                logger.error(f"❌ Config error: examples must be a list (got {type(raw_examples).__name__})")
                raw_examples = []
            
            config_data['examples'] = validate_examples(raw_examples)
            
            return ChewdocConfig(**config_data)
    return ChewdocConfig()
