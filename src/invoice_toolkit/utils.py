"""Shared utilities for configuration and Jinja environment."""

import logging
from typing import TYPE_CHECKING

import jinja2
import yaml

from invoice_toolkit.models import Config

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger("invoice_toolkit")


def _currency_filter(value, locale="de"):
    if locale == "de":
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{value:.2f}"


def create_jinja_env(template_dir: Path) -> jinja2.Environment:
    """Create a Jinja2 environment rooted at *template_dir*."""
    env = jinja2.Environment(
        trim_blocks=True,
        autoescape=False,
        loader=jinja2.FileSystemLoader(str(template_dir)),
    )
    env.filters["currency"] = _currency_filter
    return env


def load_config(file: Path) -> Config:
    """Load config file.

    Raises ValueError on parse failure instead of exiting.
    """
    try:
        with file.open("rb") as f:
            parsed_file = yaml.safe_load(f)
            config = Config(**parsed_file)
        return config
    except (OSError, yaml.YAMLError, ValueError, TypeError) as e:
        raise ValueError(f"Failed to load config from {file}: {e}") from e
