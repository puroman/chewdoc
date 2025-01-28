from ._version import __version__
import click
from chewdoc.core import analyze_package, generate_docs
from pathlib import Path
from datetime import datetime


@click.group()
@click.version_option(__version__)
def cli():
    """Generate LLM-optimized documentation from Python packages"""
    pass

@cli.command()
@click.argument("source")
@click.option("--version", help="Package version")
@click.option("--local", is_flag=True, help="Local package")
@click.option("--output", "-o", default="docs", help="Output directory")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed progress")
def chew(source, version, local, output, verbose):
    """Main command implementation"""
    start_time = datetime.now()
    
    # Determine source type
    if sum([local]) != 1:
        raise click.UsageError("Must specify exactly one of --local")

    source_type = "local"
    
    # Actual processing logic
    try:
        package_info = analyze_package(
            source=source,
            version=version,
            is_local=local,
            verbose=verbose
        )
        
        output_path = Path(output)
        
        if verbose:
            total_examples = sum(len(m.get("examples", [])) for m in package_info["modules"])
            click.echo(f"📋 Found {total_examples} usage examples across modules")
        
        generate_docs(package_info, output_path, verbose=verbose)
        
        if verbose:
            duration = datetime.now() - start_time
            click.echo(f"⏱️  Documentation chewed in {duration.total_seconds():.3f}s")
            click.echo(f"📂 Output location: {output_path.resolve()}")

    except Exception as e:
        click.echo(f"❌ Error chewing documentation: {str(e)}", err=True)
        exit(1)
