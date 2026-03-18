"""Letter subcommand."""

import logging
import subprocess
import sys
from pathlib import Path  # noqa: TC003 - needed at runtime by Typer
from typing import Annotated

import typer

from invoice_toolkit.cli.utils import (
    default_project_paths,
    execute_command,
    resolve_config_path,
    validate_paths,
)
from invoice_toolkit.letter.template import create_letter
from invoice_toolkit.models import Config
from invoice_toolkit.utils import create_jinja_env, load_yaml_model

logger = logging.getLogger(__name__)


def letter_command(
    letter_file: Annotated[Path, typer.Argument(help="Path to the letter markdown file.")],
    config_file: Annotated[Path | None, typer.Option("--config", "-c", help="Path to the config YAML file.")] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Custom output path (without extension).")
    ] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Generate without opening.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable debug logging.")] = False,
    open_pdf: Annotated[bool, typer.Option("--open-pdf/--no-open-pdf", help="Open the generated PDF.")] = True,
):
    """Create a letter."""
    paths = default_project_paths()
    jinja_env = create_jinja_env(paths.template_dir)

    resolved_config = config_file or resolve_config_path(paths.data_dir, paths.project_root)

    validate_paths(
        [
            (letter_file, "letter file"),
            (resolved_config, "config file"),
        ]
    )

    config = load_yaml_model(resolved_config, Config)

    try:
        pdf_path = create_letter(
            letter_file=letter_file,
            config=config,
            paths=paths,
            jinja_env=jinja_env,
            output=output,
        )
    except (OSError, RuntimeError, ValueError) as e:
        logger.error(f"Letter generation failed: {e}")
        sys.exit(1)

    if not dry_run and open_pdf:
        try:
            execute_command(["xdg-open", str(pdf_path)])
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            logger.warning(f"Could not open PDF viewer: {e}")
    elif dry_run:
        logger.info("Dry run mode enabled. Skipping post-generation steps.")
        logger.debug(f"Output PDF saved to: {pdf_path}")
