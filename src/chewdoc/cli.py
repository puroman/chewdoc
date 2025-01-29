from chewdoc._version import __version__
import click
from chewdoc.core import analyze_package, generate_docs
from pathlib import Path
from datetime import datetime
import sys
import traceback
import logging

logger = logging.getLogger(__name__)


@click.group()
@click.version_option(__version__)
def cli():
    """Generate LLM-optimized documentation from Python packages"""
    pass


@cli.command()
@click.argument("source", default=None, required=False)
@click.option("--version", help="Package version")
@click.option("--local", is_flag=True, help="Local package")
@click.option("--pypi", is_flag=True, help="PyPI package")
@click.option("--output", "-o", default="docs", help="Output directory")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed progress")
def chew(source, version, local, pypi, output, verbose):
    """Generate documentation for a Python package."""
    start_time = datetime.now()

    # Validate source type
    if not local and not pypi:
        raise click.UsageError("Must specify --local or --pypi")
    
    # Validate source argument
    if source is None:
        if not local:
            raise click.UsageError("Missing argument 'SOURCE'")
        source = "."
    
    # Validate output directory
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    # Actual processing logic
    try:
        result = analyze_package(
            source=source, version=version, is_local=local, verbose=verbose
        )

        # Add validation checkpoint
        invalid_examples = sum(
            1
            for m in result["modules"]
            for ex in m.get("examples", [])
            if not isinstance(ex, dict) or "code" not in ex
        )
        if invalid_examples > 0:
            logger.warning(
                f"Found {invalid_examples} malformed examples in final output"
            )

        if verbose:
            total_examples = sum(len(m.get("examples", [])) for m in result["modules"])
            click.echo(f"📋 Found {total_examples} usage examples across modules")

        generate_docs(result, output_path, verbose=verbose)

        if verbose:
            duration = datetime.now() - start_time
            click.echo(f"⏱️  Documentation chewed in {duration.total_seconds():.3f}s")
            click.echo(f"📂 Output location: {output_path.resolve()}")

        return 0  # Explicit success return code

    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        if verbose:
            logger.error(f"Stack trace:\n{traceback.format_exc()}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)
