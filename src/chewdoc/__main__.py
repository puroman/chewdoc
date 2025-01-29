import click
from chewdoc.cli import cli
import argparse
import os


def main():
    """Main entry point with improved defaults"""
    parser = argparse.ArgumentParser(description='ChewDoc: Research-focused documentation generator')
    
    # Add package argument as optional (defaults to current directory)
    parser.add_argument(
        'package',
        nargs='?',
        default='.',
        help='Package path or PyPI name (default: current directory)'
    )
    
    # Set smarter defaults
    parser.add_argument('-o', '--output', 
        default='./docs/api.myst',
        help='Output path (default: %(default)s)')
    
    # Auto-detect local mode when path exists
    parser.add_argument('-l', '--local',
        action='store_true',
        default=os.path.exists(parser.parse_args().package),
        help='Auto-enabled when path exists')
    
    # ... rest of argument parsing ...

    # Add project root detection
    if parser.parse_args().package == '.' and is_project_root():
        print(f"Generating docs for project root -> {parser.parse_args().output}")
        
def is_project_root():
    """Check for common project root indicators"""
    return any(os.path.exists(f) for f in ['pyproject.toml', 'setup.py', 'src'])


if __name__ == "__main__":
    main()
