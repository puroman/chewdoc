import os
from pathlib import Path
import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from chewed.cli import cli
from chewed._version import __version__


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_cli_local_package(tmp_path):
    """Test processing a local package"""
    runner = CliRunner()

    # Create a minimal valid package
    pkg_dir = tmp_path / "test_pkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").touch()
    (pkg_dir / "module.py").write_text("def test(): pass")

    with patch("chewed.cli.analyze_package") as mock_analyze, patch(
        "chewed.cli.generate_docs"
    ) as mock_generate:
        mock_analyze.return_value = {"package": "test_pkg", "modules": []}

        result = runner.invoke(cli, ["chew", str(pkg_dir), "-o", "docs"])
        assert result.exit_code == 0
        mock_analyze.assert_called_once()
        mock_generate.assert_called_once()


def test_invalid_cli_arguments():
    """Test CLI with missing arguments"""
    runner = CliRunner()
    result = runner.invoke(cli, ["chew"])
    assert result.exit_code != 0
    assert "Missing argument 'SOURCE'" in result.output


def test_cli_verbose_output(tmp_path):
    """Test verbose output mode"""
    runner = CliRunner()
    pkg_dir = tmp_path / "verbose_pkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").touch()

    with patch("chewed.cli.analyze_package") as mock_analyze, patch(
        "chewed.cli.generate_docs"
    ):
        mock_analyze.return_value = {"package": "verbose_pkg", "modules": []}

        result = runner.invoke(cli, ["chew", str(pkg_dir), "--verbose"])
        assert result.exit_code == 0
        assert "📦 Processing local package" in result.output


def test_cli_exception_handling(tmp_path):
    """Test error handling in CLI"""
    runner = CliRunner()
    with patch("chewed.cli.analyze_package") as mock_analyze:
        mock_analyze.side_effect = ValueError("Test error")
        result = runner.invoke(cli, ["chew", str(tmp_path)])
        assert result.exit_code != 0
        assert "Error: Test error" in result.output


def test_cli_output_directory(tmp_path):
    """Test custom output directory"""
    runner = CliRunner()
    pkg_dir = tmp_path / "test_pkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").touch()

    with patch("chewed.cli.analyze_package") as mock_analyze, patch(
        "chewed.cli.generate_docs"
    ):
        mock_analyze.return_value = {"package": "test_pkg", "modules": []}

        output_dir = tmp_path / "custom_docs"
        result = runner.invoke(cli, ["chew", str(pkg_dir), "-o", str(output_dir)])
        assert result.exit_code == 0


def test_cli_pypi_package(tmp_path):
    """Test PyPI package processing"""
    runner = CliRunner()
    
    with patch("chewed.cli.analyze_package") as mock_analyze, \
         patch("chewed.cli.generate_docs") as mock_generate, \
         patch("chewed.cli.download_package") as mock_download:
        
        mock_download.return_value = tmp_path / "downloaded_pkg"
        mock_analyze.return_value = {
            "package": "test_pkg",
            "modules": [],
            "relationships": {"dependency_graph": {}, "external_deps": []},
            "metadata": {}
        }
        
        result = runner.invoke(cli, ["chew", "requests", "--pypi", "-o", str(tmp_path / "docs")])
        assert result.exit_code == 0
        assert mock_analyze.call_count == 1
        assert mock_generate.call_count == 1
