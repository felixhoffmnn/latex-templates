"""Letter template rendering and PDF generation via Typst."""

from __future__ import annotations

import logging
import shutil
from typing import TYPE_CHECKING

from invoice_toolkit.letter.utils import load_letter
from invoice_toolkit.utils import render_typst_to_pdf

if TYPE_CHECKING:
    from pathlib import Path

    import jinja2

    from invoice_toolkit.models import Config
    from invoice_toolkit.settings import ProjectPaths

logger = logging.getLogger(__name__)


def create_letter(
    letter_file: Path,
    config: Config,
    paths: ProjectPaths,
    jinja_env: jinja2.Environment,
    output: Path | None = None,
) -> Path:
    """Create a letter and return the generated PDF path.

    Args:
        letter_file: Path to the letter markdown file with YAML frontmatter.
        config: Loaded Config object.
        paths: Project paths configuration.
        jinja_env: Jinja2 environment for template rendering.
        output: Optional custom output path (without extension).

    Returns:
        Path to the generated PDF file.
    """
    letter_out_dir = paths.out_dir / "letter"
    letter_tmp_dir = paths.tmp_dir / "letter"

    frontmatter, content = load_letter(letter_file)

    letter_out_dir.mkdir(parents=True, exist_ok=True)
    letter_tmp_dir.mkdir(parents=True, exist_ok=True)

    base_template = jinja_env.get_template("letter.typ.j2")
    generated_typ_file = letter_tmp_dir / "letter.typ"
    generated_pdf_file = letter_out_dir / "letter.pdf"

    rendered_template = base_template.render(
        config=config,
        letter=frontmatter,
        recipient=frontmatter.recipient,
        content=content,
    )

    render_typst_to_pdf(rendered_template, generated_typ_file, generated_pdf_file, paths.project_root)

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        final_path = output.with_suffix(".pdf")
        shutil.move(str(generated_pdf_file), str(final_path))
        return final_path

    return generated_pdf_file
