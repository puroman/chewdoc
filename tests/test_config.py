import pytest
from pydantic import ValidationError
from src.chewdoc.config import ChewdocConfig, load_config


def test_config_defaults():
    config = ChewdocConfig()
    assert config.exclude_patterns == [
        "__pycache__", "*.tests", "test_*", 
        ".venv*", "venv*", "env*", ".git", "dist", "build"
    ]

def test_load_invalid_config(tmp_path):
    bad_config = tmp_path / "pyproject.toml"
    bad_config.write_text("[tool.chewdoc]\ninvalid_key = 42")
    
    with pytest.raises(ValidationError):
        load_config(bad_config) 