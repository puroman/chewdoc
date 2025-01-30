from src.chewdoc.utils import safe_write
import pytest
from pathlib import Path
import ast
from src.chewdoc.config import ChewdocConfig
from src.chewdoc.utils import (
    format_function_signature,
    extract_constant_values,
    validate_ast,
    get_annotation,
)


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


def test_validate_ast_invalid_nodes():
    """Test AST validation with problematic nodes"""
    # Create invalid AST node using actual AST classes
    bad_node = ast.Module(body=[
        ast.Expr(value=ast.Dict(keys=[ast.Constant(value=1)], values=[ast.Constant(value=2)]))  # Invalid dict with key-value mismatch
    ])
    
    with pytest.raises(ValueError) as excinfo:
        validate_ast(bad_node)
    assert "invalid node types" in str(excinfo.value).lower()


def test_validate_ast_empty_with_docstring():
    """Test module with only a docstring"""
    node = ast.parse('"Module docstring"')
    validate_ast(node)  # Should not raise


def test_get_annotation_complex():
    """Test annotation formatting with complex types"""
    node = ast.parse("def f() -> Dict[str, List[int]]: pass").body[0].returns
    result = get_annotation(node, ChewdocConfig())
    assert "Dict[str, List[int]]" in result


def test_validate_ast_with_errors():
    """Test AST validation with invalid assignments"""
    # Valid empty module should pass
    validate_ast(ast.parse(""))
    
    # Create invalid AST structure directly
    invalid_node = ast.Assign(
        targets=[ast.Constant(value=123)],  # Invalid target
        value=ast.Constant(value='invalid')
    )
    invalid_tree = ast.Module(body=[invalid_node], type_ignores=[])
    
    with pytest.raises(ValueError) as excinfo:
        validate_ast(invalid_tree)
    assert "Invalid assignment target" in str(excinfo.value)
