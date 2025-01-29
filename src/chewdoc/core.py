import click
from pathlib import Path
from src.chewdoc.package_analysis import analyze_package
from src.chewdoc.doc_generation import generate_docs
from src.chewdoc.config import load_config

@click.command()
@click.argument("source", type=click.Path(exists=True))
@click.option("--output", "-o", required=True, type=click.Path(), help="Output directory")
@click.option("--local/--pypi", default=True, help="Local package or PyPI package")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def cli(source: str, output: str, local: bool, verbose: bool) -> None:
    """Main entry point for package analysis"""
    config = load_config()
    package_info = analyze_package(source, is_local=local, config=config, verbose=verbose)
    generate_docs(package_info, Path(output), verbose=verbose)
