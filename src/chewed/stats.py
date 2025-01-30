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
            "constants": {"count": 0, "files": {}},
            "examples": {"total": 0, "valid": 0, "invalid": 0},
            "tests": {"cases": 0, "assertions": 0},
            "config": {"options": 0, "rules": 0},
            "coverage": {"files": 0, "lines": 0},
        }

    def analyze_project(self, project_root: Path):
        """Main analysis entry point"""
        project_root = project_root.resolve()

        # Use proper path resolution for source files
        src_dir = project_root / "chewed"
        if not src_dir.exists():
            src_dir = project_root

        self._analyze_constants(src_dir / "constants.py")
        self._analyze_tests(project_root.parent / "tests")
        self._analyze_config(src_dir / "config.py")
        self._analyze_cli(src_dir / "cli.py")
        self._analyze_formatters(src_dir / "formatters")

    def _analyze_constants(self, const_path: Path):
        """Count constants in constants.py"""
        if not const_path.exists():
            logger.warning(f"Constants file not found at {const_path}")
            return

        try:
            with open(const_path) as f:
                tree = ast.parse(f.read())
                const_count = sum(
                    1
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Assign)
                    and any(
                        isinstance(t, ast.Name) and t.id.isupper() for t in node.targets
                    )
                )
                self.metrics["constants"]["count"] = const_count
                self.metrics["constants"]["files"][str(const_path)] = const_count
        except Exception as e:
            logger.error(f"Constant analysis failed: {str(e)}")

    def _analyze_tests(self, tests_dir: Path):
        """Count test cases and assertions"""
        if not tests_dir.exists():
            logger.warning(f"Tests directory not found at {tests_dir}")
            return

        for test_file in tests_dir.glob("test_*.py"):
            try:
                with open(test_file) as f:
                    content = f.read()
                    self.metrics["tests"]["cases"] += content.count("def test_")
                    self.metrics["tests"]["assertions"] += content.count("assert ")
            except Exception as e:
                logger.warning(f"Error analyzing test file {test_file}: {str(e)}")

    def _analyze_config(self, config_path: Path):
        """Count config options"""
        if not config_path.exists():
            logger.warning(f"Config file not found at {config_path}")
            return

        try:
            with open(config_path) as f:
                tree = ast.parse(f.read())
                self.metrics["config"]["options"] = sum(
                    1
                    for node in ast.walk(tree)
                    if isinstance(node, ast.ClassDef) and node.name == "chewedConfig"
                )
        except Exception as e:
            logger.error(f"Error: {str(e)}")

    def _analyze_cli(self, cli_path: Path):
        """Count CLI commands and options"""
        if not cli_path.exists():
            logger.warning(f"CLI file not found at {cli_path}")
            return

        try:
            with open(cli_path) as f:
                content = f.read()
                self.metrics["cli"] = {
                    "commands": content.count("@cli.command()"),
                    "options": content.count("@click.option"),
                    "arguments": content.count("@click.argument"),
                }
        except Exception as e:
            logger.warning(f"Error analyzing CLI file: {str(e)}")

    def _analyze_formatters(self, formatters_dir: Path):
        """Analyze documentation formatters"""
        if not formatters_dir.exists():
            logger.warning(f"Formatters directory not found at {formatters_dir}")
            return

        examples = 0
        for ffile in formatters_dir.glob("*.py"):
            try:
                with open(ffile) as f:
                    content = f.read()
                    examples += content.count("_format_example")
                    examples += content.count("_validate_example")
            except Exception as e:
                logger.warning(f"Error analyzing formatter file {ffile}: {str(e)}")
        self.metrics["examples"]["total"] = examples

    def display_stats(self):
        """Print formatted statistics table"""
        stats = [
            ["Constants", self.metrics["constants"]["count"]],
            ["Test Cases", self.metrics["tests"]["cases"]],
            ["Test Assertions", self.metrics["tests"]["assertions"]],
            ["Config Options", self.metrics["config"]["options"]],
            ["CLI Commands", self.metrics.get("cli", {}).get("commands", 0)],
            ["CLI Options", self.metrics.get("cli", {}).get("options", 0)],
            ["Validation Examples", self.metrics["examples"]["total"]],
        ]

        print("\n📊 Documentation Statistics:")
        print(tabulate(stats, headers=["Metric", "Count"], tablefmt="rounded_outline"))
        print("\n")
