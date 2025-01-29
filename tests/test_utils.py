from src.chewdoc.utils import safe_write
import pytest
from pathlib import Path
import ast
from src.chewdoc.config import ChewdocConfig
from src.chewdoc.utils import format_function_signature, extract_constant_values

def test_safe_write(tmp_path):
    test_file = tmp_path / "test.txt"
    safe_write(test_file, "test content")
    assert test_file.read_text() == "test content"
    
    # Test overwrite protection
    test_file.write_text("existing")
    with pytest.raises(FileExistsError):
        safe_write(test_file, "new content")

def test_safe_write_overwrite(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("existing")
    with pytest.raises(FileExistsError):
        safe_write(test_file, "new content")
    
    safe_write(test_file, "new content", overwrite=True)
    assert test_file.read_text() == "new content"

def test_format_function_signature():
    args = ast.arguments(args=[ast.arg(arg="x"), ast.arg(arg="y")])
    returns = ast.Name(id="float")
    config = ChewdocConfig()
    sig = format_function_signature(args, returns, config=config)
    assert sig == "(x, y) -> float"

def test_extract_constant_values():
    node = ast.parse("MAX_LENGTH = 100\nAPI_URL = 'https://example.com'")
    constants = extract_constant_values(node)
    assert ("MAX_LENGTH", "100") in constants
    assert ("API_URL", "'https://example.com'") in constants 