import os
import click
import logging
from pathlib import Path
from typing import Optional

from chewed.core import analyze_package
from chewed.doc_generation import generate_docs
from chewed.metadata import get_pypi_metadata
from chewed.config import chewedConfig, load_config
from chewed._version import __version__

logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version=__version__)
def cli():
    """Documentation generator for Python packages."""
    pass


@cli.command(name="chew")
@click.argument("source", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default="docs",
    help="Output directory for documentation",
)
@click.option(
    "--local/--pypi", default=True, help="Process local package or download from PyPI"
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def chew_command(source: Path, output: Path, local: bool, verbose: bool):
    """Generate documentation for a Python package."""
    try:
        # Configure logging
        logging.basicConfig(
            level=logging.INFO if verbose else logging.WARNING,
            format="%(message)s",
            force=True,
        )
        logger.setLevel(logging.INFO if verbose else logging.WARNING)

        # Validate source exists if local
        if local:
            source = source.resolve()
            if not source.exists():
                raise click.BadParameter(f"Source path does not exist: {source}")

        # Load config
        config = load_config()

        # Process package
        logger.info(f"📦 Processing {'local' if local else 'PyPI'} package: {source}")
        package_info = analyze_package(source=source, config=config, verbose=verbose)

        # Generate documentation
        output.mkdir(parents=True, exist_ok=True)
        logger.info(f"📝 Generating documentation in {output}")
        generate_docs(package_info, output)

        if verbose:
            logger.info(f"✅ Documentation generated successfully in {output}")

    except Exception as e:
        logger.error(str(e))
        raise click.ClickException(str(e))


def main():
    """Entry point for the CLI."""
    cli(prog_name="chew")


if __name__ == "__main__":
    main()
