import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from src.chewdoc.cli import cli
from src.chewdoc._version import __version__


def test_cli_local_package(tmp_path, mocker):
    runner = CliRunner()
    with patch("src.chewdoc.cli.analyze_package") as mock_analyze:
        mock_analyze.return_value = {
            "name": "testpkg",
            "modules": [],
            "internal_deps": [],
            "license": "MIT"
        }
        result = runner.invoke(cli, ["chew", str(tmp_path), "--local", "--output", str(tmp_path/"output")])
        assert result.exit_code == 0
        mock_analyze.assert_called_once()
        assert (tmp_path/"output").is_dir()
        assert (tmp_path/"output"/"index.myst").exists()


def test_invalid_cli_arguments():
    runner = CliRunner()

    # Test missing source argument
    result = runner.invoke(cli, ["chew"])
    assert result.exit_code == 2
    assert "Missing argument 'SOURCE'" in result.output

    # Test invalid option
    result = runner.invoke(cli, ["chew", "pkg", "--invalid-option"])
    assert result.exit_code == 2
    assert "No such option" in result.output


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
    # Add cleanup for version file
