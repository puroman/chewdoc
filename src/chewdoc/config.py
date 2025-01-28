"""
Configuration handling for chewdoc documentation generator
"""

from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ChewdocConfig(BaseModel):
    """Main configuration model for chewdoc"""

    exclude_patterns: List[str] = Field(
        default_factory=lambda: ["__pycache__", "*.tests", "test_*"],
        description="File patterns to exclude from processing",
    )
    known_types: Dict[str, str] = Field(
        default_factory=lambda: {
            "List": "list",
            "Dict": "dict",
            "Optional": "typing.Optional",
        },
        description="Type aliases to simplify in documentation",
    )
    output_format: str = Field(
        default="myst", description="Output format (myst, markdown, etc)"
    )
    template_dir: Optional[Path] = Field(
        None, description="Custom template directory for documentation"
    )
    enable_cross_references: bool = Field(
        True, description="Generate cross-reference links between entities"
    )
    max_example_lines: int = Field(
        10, description="Maximum lines to show in usage examples"
    )


def load_config(config_path: Optional[Path] = None) -> ChewdocConfig:
    """Load configuration from pyproject.toml or environment"""
    # Try to find pyproject.toml in current or parent directories
    if not config_path:
        current_dir = Path.cwd()
        for parent in [current_dir, *current_dir.parents]:
            candidate = parent / "pyproject.toml"
            if candidate.exists():
                config_path = candidate
                break

    config_data = {}
    if config_path and config_path.exists():
        with open(config_path, "rb") as f:
            try:
                import tomli

                data = tomli.load(f)
                config_data = data.get("tool", {}).get("chewdoc", {})
            except tomli.TOMLDecodeError:
                pass

    return ChewdocConfig(**config_data)
