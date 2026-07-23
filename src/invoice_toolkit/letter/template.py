from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from invoice_toolkit.letter.utils import load_letter
from invoice_toolkit.utils import build_sender_data, compile_template

if TYPE_CHECKING:
    from pathlib import Path

    from invoice_toolkit.models import Config
    from invoice_toolkit.settings import ProjectPaths


def create_letter(
    letter_file: Path,
    config: Config,
    paths: ProjectPaths,
    output: Path | None = None,
) -> Path:
    """Create a letter and return the generated PDF path.

    Args:
        letter_file: Path to the letter markdown file with YAML frontmatter.
        config: Loaded Config object.
        paths: Project paths configuration.
        output: Optional custom output path (without extension).

    Returns:
        Path to the generated PDF file.
    """
    letter_out_dir = paths.out_dir / "letter"

    frontmatter, content = load_letter(letter_file)

    letter_out_dir.mkdir(parents=True, exist_ok=True)

    generated_pdf_file = letter_out_dir / "letter.pdf"

    sender_data = build_sender_data(config.sender)

    data = {
        "config": sender_data,
        "letter": {
            "subject": frontmatter.subject,
            "opening": frontmatter.opening,
            "closing": frontmatter.closing,
        },
        "recipient": frontmatter.recipient.model_dump(
            mode="json",
            include={"name", "extra", "street", "zip", "city"},
        ),
        "content": content,
    }

    compile_template("letter.typ", data, generated_pdf_file, paths.template_dir)

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        final_path = output.parent / f"{output.name}.pdf"
        shutil.move(str(generated_pdf_file), str(final_path))
        return final_path

    return generated_pdf_file
