import sys
from pathlib import Path

import typst
from loguru import logger

from invoice_toolkit.letter.utils import load_letter
from invoice_toolkit.settings import (
    CONFIG_DEFAULT_FILE,
    OUT_DIR,
    PROJECT_ROOT,
    TMP_DIR,
)
from invoice_toolkit.utils import config_logging, execute_command, jinja_env, load_config, validate_paths

LETTER_OUT_DIR = OUT_DIR / "letter"
LETTER_TMP_DIR = TMP_DIR / "letter"


def create_letter(
    letter_file: Path | str | None = None,
    config_file: Path | str | None = None,
    output: Path | str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
):
    """Create a letter.

    This function will create a letter based on the given config and letter files.
    """
    config_logging(verbose)

    if letter_file is None:
        logger.error("Missing required argument: letter_file")
        sys.exit(1)

    letter_file = Path(letter_file)
    config_file = Path(config_file or CONFIG_DEFAULT_FILE)

    validate_paths(
        [
            (letter_file, "letter file"),
            (config_file, "config file"),
        ]
    )

    config = load_config(config_file)
    frontmatter, content = load_letter(letter_file)

    # Create output and tmp directory if they don't exist
    LETTER_OUT_DIR.mkdir(parents=True, exist_ok=True)
    LETTER_TMP_DIR.mkdir(parents=True, exist_ok=True)

    base_template = jinja_env.get_template("letter.typ.j2")
    generated_typ_file = LETTER_TMP_DIR / "letter.typ"
    generated_pdf_file = LETTER_OUT_DIR / "letter.pdf"

    # Render the template
    rendered_template = base_template.render(
        config=config,
        letter=frontmatter,
        content=content,
    )

    # Store typ file based on invoice number
    with generated_typ_file.open("w") as f:
        f.write(rendered_template)

    # Execute the command to generate the PDF
    try:
        typst.compile(str(generated_typ_file), output=str(generated_pdf_file), root=str(PROJECT_ROOT))
    except Exception as e:
        logger.error(f"Typst compilation failed for {generated_typ_file}: {e}")
        sys.exit(1)

    if output is not None:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        generated_pdf_file.rename(Path(f"{output}.pdf"))
        return

    if not dry_run:
        if config.settings.open_pdf_viewer:
            execute_command(["xdg-open", str(generated_pdf_file)])
    else:
        logger.info("Dry run mode enabled. Skipping post-generation steps.")
        logger.debug(f"Rendered template saved to: {generated_typ_file}")
        logger.debug(f"Output PDF saved to: {generated_pdf_file}")
