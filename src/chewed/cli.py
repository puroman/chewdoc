import os
import click
import logging
from pathlib import Path
from typing import Optional
import tempfile

from chewed.core import analyze_package
from chewed.doc_generation import generate_docs
from chewed.metadata import get_pypi_metadata
from chewed.config import chewedConfig, load_config
from chewed._version import __version__

logger = logging.getLogger(__name__)


@click.group()
@click.version_option()
def cli():
    """Documentation generator for Python packages."""
    pass


@cli.command(name="chew")
@click.argument('source', type=str)
@click.option('--output', '-o', default='docs',
              help='Output directory for documentation')
@click.option('--local/--pypi', default=True,
              help='Process local package or download from PyPI')
@click.option('--verbose', '-v', count=True,
              help='Enable verbose output')
def chew(source: str, output: str, local: bool, verbose: bool):
    """Generate documentation for a Python package."""
    try:
        logger.info("📚 Generating project documentation...")
        logger.info("🕒 Timing documentation generation...")
        
        config = load_config()
        logger.info("Loading configuration")
        
        package_info = analyze_package(source, is_local=local, config=config)
        logger.info("Analyzing package")
        
        generate_docs(package_info, Path(output), verbose=verbose)
        logger.info("Generating documentation")
        
        click.echo(f"✅ Documentation generated in {output}/")
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise click.ClickException(str(e))


if __name__ == "__main__":
    cli()

