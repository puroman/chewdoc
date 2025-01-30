import os
import click
import logging
from pathlib import Path
from typing import Optional

from chewed.core import analyze_package
from chewed.doc_generation import generate_docs
from chewed.metadata import get_pypi_metadata
from chewed.config import chewedConfig
from chewed._version import __version__

logger = logging.getLogger(__name__)

@click.command()
@click.argument('source', required=True)
@click.option('--output', '-o', default='docs', help='Output directory for documentation')
@click.option('--local/--pypi', default=True, help='Source is local package or PyPI package')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.version_option(__version__, prog_name="chewed")
def cli(source: str, output: str, local: bool, verbose: bool):
    """Generate LLM-optimized documentation for Python packages."""
    try:
        # Configure logging
        logging.basicConfig(
            level=logging.INFO if verbose else logging.WARNING,
            format='%(levelname)s: %(message)s'
        )

        # Resolve output path
        output_path = Path(output).resolve()
        output_path.mkdir(parents=True, exist_ok=True)

        # Handle PyPI package download if needed
        if not local:
            logger.info(f"🌐 Fetching PyPI package metadata for {source}")
            source = get_pypi_metadata(source)

        # Analyze package
        config = chewedConfig()
        package_info = analyze_package(
            source=str(source), 
            is_local=local, 
            config=config, 
            verbose=verbose
        )

        # Generate documentation
        generate_docs(package_info, output_path, verbose)

        # Log statistics
        if verbose:
            examples_count = sum(
                len(mod.get('examples', [])) 
                for mod in package_info.get('modules', [])
            )
            logger.info(f"📋 Found {examples_count} usage examples")

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Abort()

def main():
    cli(prog_name="chew")

if __name__ == "__main__":
    main()
