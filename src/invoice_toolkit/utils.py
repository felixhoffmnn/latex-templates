"""Shared utilities for configuration, logging, and command execution."""

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import jinja2
import yaml

from invoice_toolkit.invoice.models import Customer, Invoices
from invoice_toolkit.models import Config
from invoice_toolkit.settings import TEMPLATE_DIR

if TYPE_CHECKING:
    from pydantic import BaseModel

logger = logging.getLogger("invoice_toolkit")

jinja_env = jinja2.Environment(
    trim_blocks=True,
    autoescape=False,
    loader=jinja2.FileSystemLoader(str(TEMPLATE_DIR)),
)


def _currency_filter(value, locale="de"):
    if locale == "de":
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{value:.2f}"


jinja_env.filters["currency"] = _currency_filter


def load_config(file: Path) -> Config:
    """Load config file."""
    try:
        with file.open("rb") as f:
            parsed_file = yaml.safe_load(f)
            config = Config(**parsed_file)
        return config
    except (yaml.YAMLError, ValueError, TypeError) as e:
        logger.error(f"Failed to load config from {file}: {e}")
        sys.exit(1)


def generate_schema():
    """Generate json schemas for pydantic models."""
    schema_dir = Path("schema")
    schemas: list[type[BaseModel]] = [Config, Invoices, Customer]

    schema_dir.mkdir(exist_ok=True)

    for schema in schemas:
        with Path(f"schema/{schema.__name__.lower()}.json").open("w") as f:
            json.dump(schema.model_json_schema(), f, indent=2)
        logger.info(f"Generated schema for {schema.__name__}")


def config_logging(debug: bool):
    """Configure the logging level based on the debug flag."""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
        force=True,
    )


def validate_paths(paths: list[tuple[Path, str]]):
    """Validate that all required paths exist, logging and exiting if any are missing."""
    missing = [(path, label) for path, label in paths if not path.exists()]
    for path, label in missing:
        logger.error(f"Missing {label}: {path}")
    if missing:
        sys.exit(1)


def execute_command(command: list[str], exit_on_error: bool = False, output_file: Path | str | None = None):
    """Run a command as subprocess."""
    try:
        subprocess.run(command, check=True)
        logger.info("Command executed successfully.")
        if output_file:
            logger.info(f"Output file: {output_file}")
    except FileNotFoundError:
        logger.error(f"Command not found: {command[0]}")
        if exit_on_error:
            sys.exit(1)
    except subprocess.CalledProcessError as e:
        logger.error(f"Command execution failed: {e}")
        if exit_on_error:
            sys.exit(1)
