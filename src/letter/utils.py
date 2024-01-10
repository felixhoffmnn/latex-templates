from pathlib import Path

import pypandoc
import yaml

from src.letter.models.letter import Letter


def load_letter(file: Path) -> tuple[Letter, str]:
    """Load invoice file."""
    with file.open("rb") as f:
        parsed_file = f.read().decode("utf-8")
    frontmatter, content = parsed_file.split("---", 2)[1:]

    attributes = Letter(**yaml.safe_load(frontmatter))
    converted_content = pypandoc.convert_text(content, "latex", format="md")

    return attributes, converted_content
