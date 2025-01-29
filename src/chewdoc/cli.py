from chewdoc._version import __version__
import click
from chewdoc.core import analyze_package, generate_docs
from pathlib import Path
from datetime import datetime
import sys
import traceback
import logging
from typing import Optional, Union, List, Dict, Any
from chewdoc.config import load_config

logger = logging.getLogger(__name__)


@click.group()
@click.version_option(__version__)
def cli():
    """Generate LLM-optimized documentation from Python packages"""
    pass


@cli.command()
@click.argument("source", type=str)
@click.option("--output", "-o", required=True, type=click.Path(), help="Output directory")
@click.option("--local/--pypi", default=None, help="Local package or PyPI package")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--version", help="Package version to analyze (for PyPI packages)")
def chew(source: str, output: str, local: Optional[bool], verbose: bool, version: Optional[str] = None) -> None:
    """Main entry point for package analysis"""
    start_time = datetime.now()

    # Validate source type
    if local is None:
        raise click.UsageError("Must specify --local or --pypi")

    # Validate source path for local packages
    if local and not Path(source).exists():
        raise click.UsageError(f"Local source path does not exist: {source}")

    # Prepare output directory
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        config = load_config()
        result = analyze_package(
            source=source, 
            version=version, 
            is_local=local, 
            config=config, 
            verbose=verbose
        )

        # Normalize result to list of modules
        if isinstance(result, dict):
            result = result.get("modules", [])
        elif not isinstance(result, list):
            result = [result]

        # Add validation checkpoint
        invalid_examples = sum(
            1
            for m in result
            for ex in m.get("examples", [])
            if not isinstance(ex, dict) or "code" not in ex
        )
        if invalid_examples > 0:
            logger.warning(
                f"Found {invalid_examples} malformed examples in final output"
            )

        if verbose:
            total_examples = sum(len(m.get("examples", [])) for m in result)
            click.echo(f"📋 Found {total_examples} usage examples across modules")

        generate_docs(result, output_path, verbose=verbose)

        if verbose:
            duration = datetime.now() - start_time
            click.echo(f"⏱️  Documentation chewed in {duration.total_seconds():.3f}s")
            click.echo(f"📂 Output location: {output_path.resolve()}")

    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        if verbose:
            logger.error(f"Stack trace:\n{traceback.format_exc()}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)
