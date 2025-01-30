from chewed._version import __version__
import click
from chewed.core import analyze_package, generate_docs
from pathlib import Path
from datetime import datetime
import sys
import traceback
import logging
from typing import Optional, Union, List, Dict, Any
from chewed.config import load_config

logger = logging.getLogger(__name__)


@click.group()
@click.version_option(__version__)
def cli():
    """Generate LLM-optimized documentation from Python packages"""
    pass


@cli.command()
@click.argument("source", type=click.Path(exists=True))
@click.option(
    "--output", "-o", required=True, type=click.Path(), help="Output directory"
)
@click.option("--local/--pypi", default=True, help="Local package or PyPI package")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def chew(source: str, output: str, local: bool, verbose: bool) -> None:
    """Main entry point for package analysis"""
    config = load_config()
    package_info = analyze_package(
        source=source, is_local=local, config=config, verbose=verbose
    )
    generate_docs(package_info, Path(output))
