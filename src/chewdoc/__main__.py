import click
from chewdoc.cli import cli


def main():
    """Entry point for the chewdoc CLI"""
    try:
        cli()
    except click.UsageError as e:
        click.echo(str(e), err=True)
        exit(2)
    except Exception as e:
        click.echo(f"An unexpected error occurred: {e}", err=True)
        exit(1)


if __name__ == "__main__":
    main()
