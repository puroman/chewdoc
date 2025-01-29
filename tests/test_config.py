import pytest
from pydantic import ValidationError
from src.chewdoc.config import ChewdocConfig, load_config
import tomllib


def test_config_defaults():
    config = ChewdocConfig()
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
    bad_config.write_text("[tool.chewdoc]\ninvalid_key = 42")

    with pytest.raises(ValidationError):
        load_config(bad_config)


def test_config_validation():
    """Test config validation with invalid values"""
    with pytest.raises(ValueError):
        ChewdocConfig(max_example_lines=-5)

    with pytest.raises(ValueError):
        ChewdocConfig(theme="invalid_theme")


def test_config_from_toml(tmp_path):
    """Test loading config from TOML file"""
    config_file = tmp_path / "chewdoc.toml"
    config_file.write_text("""
    [tool.chewdoc]
    max_example_lines = 20
    """)  # Removed invalid theme
    
    with open(config_file, "rb") as f:
        config_data = tomllib.load(f)
    
    config = ChewdocConfig(**config_data.get("tool", {}).get("chewdoc", {}))
    assert config.max_example_lines == 20
