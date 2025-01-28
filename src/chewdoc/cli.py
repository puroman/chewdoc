import click
from chewdoc.core import analyze_package, generate_docs
from pathlib import Path
from datetime import datetime


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Generate LLM-optimized documentation from Python packages"""
    if ctx.invoked_subcommand is None:
        raise click.UsageError("Missing command. Use 'chew' directly.")


@cli.command()
@click.argument("target")
@click.option("--local", is_flag=True, help="Analyze local directory")
@click.option("--pypi", is_flag=True, help="Analyze PyPI package")
@click.option("--url", help="Analyze from Git URL")
@click.option("--version", help="Specify package version (PyPI only)")
@click.option("--output", "-o", type=click.Path(), default="chewdoc-output", 
             help="Output directory path", show_default=True)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed progress")
def chew(target, local, pypi, url, version, output, verbose):
    """Generate documentation for a Python package/module"""
    start_time = datetime.now()
    
    # Determine source type
    if sum([local, pypi, url is not None]) != 1:
        raise click.UsageError("Must specify exactly one of --local, --pypi, or --url")

    source_type = "local" if local else "pypi" if pypi else "url"
    
    # Actual processing logic
    try:
        package_info = analyze_package(
            source=target,
            version=version,
            is_local=local,
            verbose=verbose
        )
        
        output_path = Path(output)
        generate_docs(package_info, output_path, verbose=verbose)
        
        if verbose:
            duration = datetime.now() - start_time
            click.echo(f"⏱️  Documentation chewed in {duration.total_seconds():.3f}s")
            click.echo(f"📂 Output location: {output_path.resolve()}")

    except Exception as e:
        click.echo(f"❌ Error chewing documentation: {str(e)}", err=True)
        exit(1)
