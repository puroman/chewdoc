"""
Configuration handling for chewed documentation generator
"""

from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict, ValidationError
from chewed.constants import (  # Updated imports
    DEFAULT_EXCLUSIONS,
    TEMPLATE_VERSION,
    TYPE_ALIASES,
)
import logging
from importlib import resources

try:
    # Python 3.11+ standard library
    import tomllib
except ModuleNotFoundError:
    # Fallback for Python <3.11
    import tomli as tomllib

logger = logging.getLogger(__name__)


class chewedConfig(BaseModel):
    """Main configuration model for chewed"""

    exclude_patterns: List[str] = Field(
        default=DEFAULT_EXCLUSIONS,
        description="File patterns to exclude from processing",
    )
    template_version: str = Field(
        TEMPLATE_VERSION, description="Version identifier for documentation templates"
    )
    known_types: Dict[str, str] = Field(
        default=TYPE_ALIASES,
        description="Type aliases for simplifying complex annotations",
    )
    output_format: str = Field(
        default="myst", description="Output format (myst/markdown)"
    )
    template_dir: Optional[Path] = Field(
        default=None, description="Custom template directory"
    )
    enable_cross_references: bool = Field(
        default=True, description="Generate cross-module links"
    )
    max_example_lines: int = Field(
        default=10, ge=1, description="Max lines in usage examples"
    )
    allow_namespace_packages: bool = Field(
        True, description="Recognize namespace packages without __init__.py"
    )
    temp_dir: Path = Field(
        default_factory=lambda: Path("/tmp/chewed"),
        description="Temporary directory for package processing",
    )
    include_tests: bool = Field(
        False, description="Include test modules in documentation"
    )
    module_discovery_patterns: List[str] = Field(
        default=["**/*.py", "!test_*.py", "!*/tests/*", "!*/_*"],
        description="File patterns for module discovery (include/exclude)",
    )
    namespace_fallback: bool = Field(
        True, description="Create minimal documentation for empty namespace packages"
    )

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def from_toml(cls, path: Path) -> "chewedConfig":
        """Load config from TOML file"""
        config_data = tomllib.load(path)
        return cls(**config_data.get("tool", {}).get("chewed", {}))


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
                validated.append({"type": "doctest", "code": ex, "output": ""})
                continue

            # Require dictionary format
            if not isinstance(ex, dict):
                raise TypeError(f"Example #{idx} is {type(ex).__name__}, expected dict")

            # Check required fields
            if "code" not in ex and "content" not in ex:
                raise ValueError(f"Example #{idx} missing code/content")

            validated.append(
                {
                    "type": ex.get("type", "doctest"),
                    "code": str(ex.get("code", ex.get("content", ""))),
                    "output": str(ex.get("output", ex.get("result", ""))),
                }
            )

        except (TypeError, ValueError) as e:
            logger.error(f"Config validation failed for example #{idx}: {e}")

    return validated


def load_config(path: Optional[Path] = None) -> chewedConfig:
    """Load configuration from file or return defaults"""
    if path and path.exists():
        with open(path, "rb") as f:
            config_data = tomllib.load(f).get("tool", {}).get("chewed", {})

            # Add type enforcement for examples
            raw_examples = config_data.get("examples", [])
            if not isinstance(raw_examples, list):
                logger.error(
                    f"❌ Config error: examples must be list (got {type(raw_examples).__name__})"
                )
                raw_examples = []

            config_data["examples"] = validate_examples(raw_examples)

            return chewedConfig(**config_data)
    return chewedConfig()
