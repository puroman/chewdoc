import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from src.chewdoc.cli import cli
from src.chewdoc._version import __version__


def test_cli_local_package(tmp_path):
    runner = CliRunner()
    with patch("src.chewdoc.cli.analyze_package") as mock_analyze, \
         patch("src.chewdoc.cli.MystWriter") as mock_writer:
        
        mock_analyze.return_value = {"name": "testpkg"}
        result = runner.invoke(cli, ["chew", str(tmp_path), "--local"])
        
        assert result.exit_code == 0
        mock_analyze.assert_called_once()
        mock_writer.return_value.generate.assert_called_once()


def test_cli_pypi_package():
    runner = CliRunner()
    with patch("src.chewdoc.cli.analyze_package") as mock_analyze:
        mock_analyze.return_value = {"name": "requests"}
        result = runner.invoke(cli, ["chew", "requests", "--version", "2.28.1"])
        
        assert result.exit_code == 0
        mock_analyze.assert_called_once_with(
            source="requests", version="2.28.1", is_local=False
        )


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


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Generate LLM-optimized documentation" in result.output


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output
