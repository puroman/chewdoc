import click
from .core import analyze_package, generate_docs

@click.group()
def cli():
    """Generate LLM-optimized documentation from Python packages"""
    pass

@cli.command()
@click.argument("source")
@click.option("--version", help="Package version (for PyPI packages)")
@click.option("--output", "-o", required=True, help="Output file path")
@click.option("--local", is_flag=True, help="Treat source as local path")
def package(source, version, output, local):
    """Process a Python package"""
    click.echo(f"Analyzing package: {source}")
    
    pkg_info = analyze_package(
        source=source,
        version=version,
        is_local=local
    )
    
    generate_docs(pkg_info, output)
    click.echo(f"Documentation generated at {output}")

@cli.command()
@click.argument("module_path")
@click.option("--output", "-o", help="Output file path")
def module(module_path, output):
    """Process a single Python module"""
    click.echo(f"Analyzing module: {module_path}")
    # Module analysis implementation 