import pytest
from pydantic import ValidationError
from src.chewed.config import chewedConfig, load_config
import tomllib


def test_config_defaults():
    config = chewedConfig()
    assert config.exclude_patterns == [
        "__pycache__",
        ".*",  # Updated pattern
        "tests/*",
        "docs/*",
        "build/*",
        "dist/*",
        "venv*",
        ".venv*",
        "env*",
    ]


def test_load_invalid_config(tmp_path):
    bad_config = tmp_path / "pyproject.toml"
    bad_config.write_text("[tool.chewed]\ninvalid_key = 42")

    with pytest.raises(ValidationError):
        load_config(bad_config)


def test_config_validation():
    """Test config validation with invalid values"""
    with pytest.raises(ValueError):
        chewedConfig(max_example_lines=-5)

    with pytest.raises(ValueError):
        chewedConfig(theme="invalid_theme")


def test_config_from_toml(tmp_path):
    """Test loading config from TOML file"""
    config_file = tmp_path / "chewed.toml"
    config_file.write_text(
        """
    [tool.chewed]
    max_example_lines = 20
    """
    )  # Removed invalid theme

    with open(config_file, "rb") as f:
        config_data = tomllib.load(f)

    config = chewedConfig(**config_data.get("tool", {}).get("chewed", {}))
    assert config.max_example_lines == 20
