"""
Documentation statistics collection and reporting
"""

from pathlib import Path
import ast
from typing import Dict, Any
import logging
from tabulate import tabulate

logger = logging.getLogger(__name__)

class StatsCollector:
    def __init__(self):
        self.metrics = {
            'constants': {'count': 0, 'files': {}},
            'examples': {'total': 0, 'valid': 0, 'invalid': 0},
            'tests': {'cases': 0, 'assertions': 0},
            'config': {'options': 0, 'rules': 0},
            'coverage': {'files': 0, 'lines': 0}
        }
    
    def analyze_project(self, project_root: Path):
        """Main analysis entry point"""
        self._analyze_constants(project_root / 'src' / 'chewed' / 'constants.py')
        self._analyze_tests(project_root / 'tests')
        self._analyze_config(project_root / 'src' / 'chewed' / 'config.py')
        self._analyze_cli(project_root / 'src' / 'chewed' / 'cli.py')
        self._analyze_formatters(project_root / 'src' / 'chewed' / 'formatters')
        
    def _analyze_constants(self, const_path: Path):
        """Count constants in constants.py"""
        try:
            with open(const_path) as f:
                tree = ast.parse(f.read())
                const_count = sum(1 for node in ast.walk(tree) 
                                if isinstance(node, ast.Assign)
                                and any(isinstance(t, ast.Name) and t.id.isupper() 
                                        for t in node.targets))
                self.metrics['constants']['count'] = const_count
                self.metrics['constants']['files'][str(const_path)] = const_count
        except Exception as e:
            logger.error(f"Constant analysis failed: {str(e)}")

    def _analyze_tests(self, tests_dir: Path):
        """Count test cases and assertions"""
        for test_file in tests_dir.glob('test_*.py'):
            with open(test_file) as f:
                content = f.read()
                self.metrics['tests']['cases'] += content.count('def test_')
                self.metrics['tests']['assertions'] += content.count('assert ')

    def _analyze_config(self, config_path: Path):
        """Count config options"""
        with open(config_path) as f:
            tree = ast.parse(f.read())
            self.metrics['config']['options'] = sum(
                1 for node in ast.walk(tree) 
                if isinstance(node, ast.ClassDef) and node.name == 'chewedConfig'
            )

    def _analyze_cli(self, cli_path: Path):
        """Count CLI commands and options"""
        with open(cli_path) as f:
            content = f.read()
            self.metrics['cli'] = {
                'commands': content.count('@cli.command()'),
                'options': content.count('@click.option'),
                'arguments': content.count('@click.argument')
            }

    def _analyze_formatters(self, formatters_dir: Path):
        """Analyze documentation formatters"""
        examples = 0
        for ffile in formatters_dir.glob('*.py'):
            with open(ffile) as f:
                content = f.read()
                examples += content.count('_format_example')
                examples += content.count('_validate_example')
        self.metrics['examples']['total'] = examples

    def display_stats(self):
        """Print formatted statistics table"""
        stats = [
            ['Constants', self.metrics['constants']['count']],
            ['Test Cases', self.metrics['tests']['cases']],
            ['Test Assertions', self.metrics['tests']['assertions']],
            ['Config Options', self.metrics['config']['options']],
            ['CLI Commands', self.metrics.get('cli', {}).get('commands', 0)],
            ['CLI Options', self.metrics.get('cli', {}).get('options', 0)],
            ['Validation Examples', self.metrics['examples']['total']]
        ]
        
        print("\n📊 Documentation Statistics:")
        print(tabulate(stats, headers=['Metric', 'Count'], tablefmt='rounded_outline'))
        print("\n") 