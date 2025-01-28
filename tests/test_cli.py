import pytest
from click.testing import CliRunner
from src.chewdoc.cli import cli
from unittest.mock import patch

def test_cli_package_command(tmp_path):
    """Test package command with valid local package"""
    # Create minimal package structure
    (tmp_path / "__init__.py").write_text('"""Test package"""')
    (tmp_path / "module.py").write_text('def test_fn():\n    """Test docstring"""')
    
    runner = CliRunner()
    with patch('src.chewdoc.cli.analyze_package') as mock_analyze, \
         patch('src.chewdoc.cli.generate_docs') as mock_generate:
        
        mock_analyze.return_value = {"name": "testpkg"}  # Minimal valid response
        output_path = tmp_path / "out.md"
        
        result = runner.invoke(cli, [
            'package', 
            str(tmp_path),
            '--local',
            '--output', str(output_path)
        ])
        
        assert result.exit_code == 0, f"CLI failed: {result.exception}"
        mock_analyze.assert_called_once_with(
            source=str(tmp_path),
            version=None,
            is_local=True
        )
        mock_generate.assert_called_once()

def test_cli_version_handling(tmp_path):
    """Test PyPI package version handling"""
    runner = CliRunner()
    with patch('src.chewdoc.cli.analyze_package') as mock_analyze:
        mock_analyze.return_value = {"name": "requests"}  # Dummy response
        output_path = tmp_path / "out.md"
        
        result = runner.invoke(cli, [
            'package', 
            'requests',
            '--version', '2.28.1',
            '--output', str(output_path)
        ])
        
        assert result.exit_code == 0, f"CLI failed: {result.exception}"
        mock_analyze.assert_called_once_with(
            source='requests',
            version='2.28.1',
            is_local=False
        ) 

def test_cli_module_command(tmp_path):
    runner = CliRunner()
    with patch('src.chewdoc.cli.analyze_package') as mock_analyze:
        mock_analyze.return_value = {"name": "testmod"}
        module_path = tmp_path / "testmod.py"
        module_path.write_text('"""Test module"""')  # Create the file
        output_path = tmp_path / "mod.md"
        
        result = runner.invoke(cli, [
            'module',
            str(module_path),
            '--output', str(output_path)
        ])
        
        assert result.exit_code == 0
        assert "Analyzing module" in result.output

def test_invalid_cli_arguments():
    runner = CliRunner()
    
    # Test no arguments
    result = runner.invoke(cli)
    assert result.exit_code == 2
    assert "Missing command" in result.output
    
    # Test invalid command
    result = runner.invoke(cli, ["invalid"])
    assert result.exit_code == 2
    assert "No such command" in result.output 