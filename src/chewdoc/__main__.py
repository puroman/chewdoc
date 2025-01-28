from chewdoc.cli import cli
import click

@click.group()
@click.pass_context
def cli(ctx):
    """Generate LLM-optimized documentation from Python packages"""
    if ctx.invoked_subcommand is None:
        raise click.UsageError("Missing command. Use 'package' or 'module'.")

@click.command()
@click.argument("package", required=True)
@click.option("--format", default="myst", type=click.Choice(["myst"]), help="Output format")
def cli(package: str, format: str):
    click.echo(f"Analyzing {package}...")

if __name__ == '__main__':
    cli() 