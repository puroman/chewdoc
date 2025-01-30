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
        logger.debug("Initializing StatsCollector")
        self.metrics = {
            "constants": {"count": 0, "files": {}},
            "examples": {"total": 0, "valid": 0, "invalid": 0},
            "tests": {"cases": 0, "assertions": 0},
            "config": {"options": 0, "rules": 0},
            "coverage": {"files": 0, "lines": 0},
        }
        logger.debug(f"Initialized metrics structure: {self.metrics}")

    def analyze_project(self, project_root: Path):
        """Main analysis entry point"""
        logger.info(f"Starting project analysis at {project_root}")
        project_root = project_root.resolve()

        # Use proper path resolution for source files
        src_dir = project_root / "chewed"
        if not src_dir.exists():
            logger.debug("chewed directory not found, using project root")
            src_dir = project_root

        logger.debug(f"Analyzing source directory: {src_dir}")
        self._analyze_constants(src_dir / "constants.py")
        self._analyze_tests(project_root.parent / "tests")
        self._analyze_config(src_dir / "config.py")
        self._analyze_cli(src_dir / "cli.py")
        self._analyze_formatters(src_dir / "formatters")
        logger.info("Project analysis completed")

    def _analyze_constants(self, const_path: Path):
        """Count constants in constants.py"""
        logger.info(f"Analyzing constants in {const_path}")
        if not const_path.exists():
            logger.warning(f"Constants file not found at {const_path}")
            return

        try:
            with open(const_path) as f:
                logger.debug("Parsing constants file")
                tree = ast.parse(f.read())
                const_count = sum(
                    1
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Assign)
                    and any(
                        isinstance(t, ast.Name) and t.id.isupper() for t in node.targets
                    )
                )
                logger.debug(f"Found {const_count} constants")
                self.metrics["constants"]["count"] = const_count
                self.metrics["constants"]["files"][str(const_path)] = const_count
        except Exception as e:
            logger.error(f"Constant analysis failed: {str(e)}", exc_info=True)

    def _analyze_tests(self, tests_dir: Path):
        """Count test cases and assertions"""
        logger.info(f"Analyzing tests in {tests_dir}")
        if not tests_dir.exists():
            logger.warning(f"Tests directory not found at {tests_dir}")
            return

        for test_file in tests_dir.glob("test_*.py"):
            logger.debug(f"Analyzing test file: {test_file}")
            try:
                with open(test_file) as f:
                    content = f.read()
                    test_cases = content.count("def test_")
                    assertions = content.count("assert ")
                    logger.debug(f"Found {test_cases} test cases and {assertions} assertions")
                    self.metrics["tests"]["cases"] += test_cases
                    self.metrics["tests"]["assertions"] += assertions
            except Exception as e:
                logger.warning(f"Error analyzing test file {test_file}: {str(e)}", exc_info=True)

    def _analyze_config(self, config_path: Path):
        """Count config options"""
        logger.info(f"Analyzing config at {config_path}")
        if not config_path.exists():
            logger.warning(f"Config file not found at {config_path}")
            return

        try:
            with open(config_path) as f:
                logger.debug("Parsing config file")
                tree = ast.parse(f.read())
                options = sum(
                    1
                    for node in ast.walk(tree)
                    if isinstance(node, ast.ClassDef) and node.name == "chewedConfig"
                )
                logger.debug(f"Found {options} config options")
                self.metrics["config"]["options"] = options
        except Exception as e:
            logger.error(f"Config analysis failed: {str(e)}", exc_info=True)

    def _analyze_cli(self, cli_path: Path):
        """Count CLI commands and options"""
        logger.info(f"Analyzing CLI at {cli_path}")
        if not cli_path.exists():
            logger.warning(f"CLI file not found at {cli_path}")
            return

        try:
            with open(cli_path) as f:
                content = f.read()
                commands = content.count("@cli.command()")
                options = content.count("@click.option")
                arguments = content.count("@click.argument")
                logger.debug(f"Found {commands} commands, {options} options, {arguments} arguments")
                self.metrics["cli"] = {
                    "commands": commands,
                    "options": options,
                    "arguments": arguments,
                }
        except Exception as e:
            logger.warning(f"Error analyzing CLI file: {str(e)}", exc_info=True)

    def _analyze_formatters(self, formatters_dir: Path):
        """Analyze documentation formatters"""
        logger.info(f"Analyzing formatters in {formatters_dir}")
        if not formatters_dir.exists():
            logger.warning(f"Formatters directory not found at {formatters_dir}")
            return

        examples = 0
        for ffile in formatters_dir.glob("*.py"):
            logger.debug(f"Analyzing formatter file: {ffile}")
            try:
                with open(ffile) as f:
                    content = f.read()
                    format_examples = content.count("_format_example")
                    validate_examples = content.count("_validate_example")
                    examples += format_examples + validate_examples
                    logger.debug(f"Found {format_examples + validate_examples} examples")
            except Exception as e:
                logger.warning(f"Error analyzing formatter file {ffile}: {str(e)}", exc_info=True)
        self.metrics["examples"]["total"] = examples
        logger.debug(f"Total examples found: {examples}")

    def display_stats(self):
        """Print formatted statistics table"""
        logger.info("Displaying statistics")
        stats = [
            ["Constants", self.metrics["constants"]["count"]],
            ["Test Cases", self.metrics["tests"]["cases"]],
            ["Test Assertions", self.metrics["tests"]["assertions"]],
            ["Config Options", self.metrics["config"]["options"]],
            ["CLI Commands", self.metrics.get("cli", {}).get("commands", 0)],
            ["CLI Options", self.metrics.get("cli", {}).get("options", 0)],
            ["Validation Examples", self.metrics["examples"]["total"]],
        ]

        logger.debug(f"Prepared stats table: {stats}")
        print("\n📊 Documentation Statistics:")
        print(tabulate(stats, headers=["Metric", "Count"], tablefmt="rounded_outline"))
        print("\n")
