"""Utilities for loading letter files with YAML frontmatter."""

from typing import TYPE_CHECKING

import pypandoc
import yaml

from invoice_toolkit.letter.models.letter import Letter

if TYPE_CHECKING:
    from pathlib import Path


def load_letter(file: Path) -> tuple[Letter, str]:
    """Load letter file with YAML frontmatter and Markdown body.

    Raises OSError if the file cannot be read, ValueError for invalid
    frontmatter or YAML, and RuntimeError if pandoc conversion fails.
    """
    try:
        content = file.read_text(encoding="utf-8")
    except OSError as e:
        raise OSError(f"Failed to read letter file {file}: {e}") from e

    expected_parts = 3  # before, frontmatter, body
    parts = content.split("---", 2)
    if len(parts) < expected_parts:
        raise ValueError(f"Invalid frontmatter in {file}: expected '---' delimiters around YAML header")

    frontmatter_raw, body = parts[1], parts[2]

    try:
        attributes = Letter(**yaml.safe_load(frontmatter_raw))
    except (yaml.YAMLError, ValueError, TypeError) as e:
        raise ValueError(f"Failed to parse frontmatter in {file}: {e}") from e

    try:
        converted_content = pypandoc.convert_text(body, "typst", format="md")
    except RuntimeError as e:
        raise RuntimeError(f"Pandoc conversion failed for {file}: {e}") from e

    return attributes, converted_content
