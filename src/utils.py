import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

import jinja2
import yaml
from loguru import logger

from src.invoice.models import Customer, Invoices
from src.models import Config

if TYPE_CHECKING:
    from pydantic import BaseModel

latex_jinja_env = jinja2.Environment(
    block_start_string="((*",
    block_end_string="*))",
    variable_start_string="(((",
    variable_end_string=")))",
    comment_start_string="((=",
    comment_end_string="=))",
    trim_blocks=True,
    autoescape=False,
    loader=jinja2.FileSystemLoader("template"),
)


def load_config(file: Path) -> Config:
    """Load config file."""
    with file.open("rb") as f:
        parsed_file = yaml.safe_load(f)
        config = Config(**parsed_file)
    return config


def compose_latex_command(out_dir: Path, tex_file: Path, verbose: bool):
    """Compose the latex command.

    This function will compose the latex command to generate a pdf from a tex file.
    The generation will take place within a container
    """
    return [
        os.environ.get("CONTAINER_RUNTIME", "podman"),
        "run",
        "--rm",
        "-it",
        "-v",
        f"{Path.cwd()}:/app:z",
        "-w",
        "/app",
        "--userns",
        f"keep-id:uid={os.getuid()},gid={os.getgid()}",
        "texlive/texlive:latest-full",
        "latexmk",
        f"-output-directory={out_dir}",
        "-pdf",
        "-verbose" if verbose else "-quiet",
        str(tex_file),
    ]


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
