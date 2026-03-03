from pathlib import Path

import pypandoc
import yaml

from invoice_toolkit.letter.models.letter import Letter


def load_letter(file: Path) -> tuple[Letter, str]:
    """Load letter file with YAML frontmatter and Markdown body."""
    content = file.read_text(encoding="utf-8")

    expected_parts = 3  # before, frontmatter, body
    parts = content.split("---", 2)
    if len(parts) < expected_parts:
        raise ValueError(f"Invalid frontmatter in {file}: expected '---' delimiters around YAML header")

    frontmatter_raw, body = parts[1], parts[2]

    attributes = Letter(**yaml.safe_load(frontmatter_raw))
    converted_content = pypandoc.convert_text(body, "typst", format="md")

    return attributes, converted_content
