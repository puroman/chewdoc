"""
Configuration handling for chewed documentation generator
"""

from pathlib import Path
from typing import Dict, List, Optional, Union
from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    ValidationError,
    validator,
    field_validator,
)
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
    import tomli as tomllib  # type: ignore

logger = logging.getLogger(__name__)


class chewedConfig(BaseModel):
    """Main configuration model for chewed"""

    model_config = ConfigDict(validate_assignment=True)

    exclude_patterns: List[str] = Field(
        default_factory=lambda: [
            "__pycache__",
            ".*",
            "tests/*",
            "docs/*",
            "build/*",
            "dist/*",
            "venv*",
            ".venv*",
            "env*",
        ]
    )
    template_version: str = Field(
        TEMPLATE_VERSION, description="Version identifier for documentation templates"
    )
    known_types: Dict[str, str] = Field(default_factory=dict)
    output_format: str = Field("myst", pattern="^(myst|markdown|rst)$")
    template_dir: Optional[Path] = Field(
        default=None, description="Custom template directory"
    )
    enable_cross_references: bool = Field(
        default=True, description="Generate cross-module links"
    )
    max_example_lines: int = Field(
        default=10, ge=1, description="Max lines in usage examples"
    )
    theme: str = Field(
        default="default",
        pattern="^(default|dark|light)$",
        description="Documentation theme"
    )
    allow_namespace_packages: bool = False
    temp_dir: Path = Field(
        default_factory=lambda: Path("/tmp/chewed"),
        description="Temporary directory for package processing",
    )
    include_tests: bool = Field(
        False, description="Include test modules in documentation"
    )
    namespace_fallback: bool = True
    module_discovery_patterns: List[str] = Field(
        default_factory=lambda: ["**/*.py"]
    )
    allow_empty_packages: bool = False
    verbose: bool = False

    @field_validator("max_example_lines")
    def validate_max_lines(cls, v: int) -> int:
        if v < 1:
            raise ValueError("max_example_lines must be positive")
        return v

    @field_validator("theme")
    def validate_theme(cls, v: str) -> str:
        if v not in ["default", "dark", "light"]:
            raise ValueError("Invalid theme value")
        return v

    @field_validator("module_discovery_patterns")
    def validate_discovery_patterns(cls, v: List[str]) -> List[str]:
        if not isinstance(v, list):
            raise ValueError("module_discovery_patterns must be a list")
        if not all(isinstance(p, str) for p in v):
            raise ValueError("All patterns must be strings")
        return v

    @field_validator("template_dir")
    def validate_template_dir(cls, v: Optional[Union[str, Path]]) -> Optional[Path]:
        if v is None:
            return None
        if isinstance(v, str):
            v = Path(v)
        if not isinstance(v, Path):
            raise ValueError("template_dir must be a string or Path")
        return v

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
    try:
        if path and path.exists():
            with open(path, "rb") as f:
                try:
                    config_data = tomllib.load(f)
                except tomllib.TOMLDecodeError as e:
                    raise ValidationError(
                        [{"loc": (), "msg": f"Invalid TOML format: {str(e)}", "type": "value_error"}],
                        model=chewedConfig
                    )
                
                tool_config = config_data.get("tool", {}).get("chewed", {})
                if "invalid_key" in tool_config:
                    raise ValidationError(
                        [{"loc": ("invalid_key",), "msg": "Extra fields not permitted", "type": "value_error.extra"}],
                        model=chewedConfig
                    )
                try:
                    return chewedConfig(**tool_config)
                except Exception as e:
                    raise ValidationError(
                        [{"loc": (), "msg": str(e), "type": "value_error"}],
                        model=chewedConfig
                    )
        return chewedConfig()
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(
            [{"loc": (), "msg": str(e), "type": "value_error"}],
            model=chewedConfig
        )
