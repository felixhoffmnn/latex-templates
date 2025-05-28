import json
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import jinja2
import yaml
from loguru import logger

from src.invoice.models import Customer, Invoices
from src.models import Config

if TYPE_CHECKING:
    from pydantic import BaseModel

jinja_env = jinja2.Environment(
    trim_blocks=True,
    autoescape=False,
    loader=jinja2.FileSystemLoader("template"),
)


def is_ci():
    """Check if the code is running in a CI environment."""
    return "CI" in os.environ or "GITHUB_ACTIONS" in os.environ


def load_config(file: Path) -> Config:
    """Load config file."""
    with file.open("rb") as f:
        parsed_file = yaml.safe_load(f)
        config = Config(**parsed_file)
    return config


def generate_schema():
    """Generate json schemas for pydantic models."""
    schema_dir = Path("schema")
    schemas: list[BaseModel] = [Config, Invoices, Customer]

    # Delete existing schemas
    if schema_dir.exists():
        for file in schema_dir.iterdir():
            file.unlink()
    else:
        schema_dir.mkdir()

    for schema in schemas:
        with Path(f"schema/{schema.__name__.lower()}.json").open("w") as f:
            json.dump(schema.model_json_schema(), f, indent=2)
        logger.info(f"Generated schema for {schema.__name__}")


def config_logging(debug: bool):
    """Configure the logging level based on the debug flag."""
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if debug else "INFO")


def execute_command(command: list[str], exit_on_error: bool = False, output_file: Path | str | None = None):
    """Run a command as subprocess."""
    try:
        subprocess.run(command, check=True)
        logger.success("Command executed successfully.")
        if output_file:
            logger.info(f"Output file: {output_file}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Command execution failed: {e}")

        if exit_on_error:
            logger.error("Exiting due to command failure.")
            sys.exit(1)
