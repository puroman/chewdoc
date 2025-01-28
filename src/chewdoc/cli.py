import click
from chewdoc.core import analyze_package, generate_docs
from pathlib import Path
from datetime import datetime


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Generate LLM-optimized documentation from Python packages"""
    if ctx.invoked_subcommand is None:
        raise click.UsageError("Missing command. Use 'package' or 'module'.")


@cli.command()
@click.argument("source")
@click.option("--version", help="Specify package version")
@click.option("--local", is_flag=True, help="Analyze local package")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed progress")
@click.option(
    "--output", type=click.Path(), default="docs.myst", help="Output file path"
)
def package(source, version, local, output, verbose):
    """Analyze a Python package"""
    start_time = datetime.now()
    package_info = analyze_package(
        source=source, version=version, is_local=local, verbose=verbose)
    generate_docs(package_info, Path(output), verbose=verbose)
    
    if verbose:
        duration = datetime.now() - start_time
        click.echo(f"⏱️  Total execution time: {duration.total_seconds():.3f}s")


@cli.command()
@click.argument("module_path", type=click.Path(exists=True))
@click.option(
    "--output", type=click.Path(), default="module_docs.myst", help="Output file path"
)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed progress")
def module(module_path, output, verbose):
    """Analyze a single Python module"""
    click.echo("Analyzing module")
    package_info = analyze_package(source=module_path, is_local=True, verbose=verbose)
    generate_docs(package_info, output, verbose=verbose)
