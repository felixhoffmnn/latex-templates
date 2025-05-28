from pathlib import Path

import typst
from loguru import logger

from src.letter.utils import load_letter
from src.settings import (
    CONFIG_DEFAULT_FILE,
    CONFIG_EXAMPLE_FILE,
    EXAMPLE_DIR,
    LETTER_DEFAULT_FILE,
    LETTER_EXAMPLE_FILE,
    OUT_DIR,
    TMP_DIR,
)
from src.utils import config_logging, execute_command, jinja_env, load_config

LETTER_OUT_DIR = OUT_DIR / "letter"
LETTER_TMP_DIR = TMP_DIR / "letter"


def create_letter(
    letter_file: Path | str | None = None,
    config_file: Path | str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
):
    """Create a letter.

    This function will create a letter based on the given config and letter files.
    """
    config_logging(verbose)

    example_mode = letter_file is None or config_file is None
    destination_path = LETTER_OUT_DIR / "letter.pdf"

    if example_mode:
        letter_file = LETTER_EXAMPLE_FILE
        config_file = CONFIG_EXAMPLE_FILE

        logger.warning("No config files specified. Using example config files.")

    letter_file = Path(letter_file or LETTER_DEFAULT_FILE)
    config_file = Path(config_file or CONFIG_DEFAULT_FILE)

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
    typst.compile(str(generated_typ_file), output=str(generated_pdf_file), root="../../")

    # Only run the PDF generation command if not in dry run mode
    if not dry_run:
        # If example mode, copy the generated PDF to the example directory
        if example_mode:
            Path.rename(destination_path, EXAMPLE_DIR / "letter.example.pdf")
            destination_path = EXAMPLE_DIR / "letter.example.pdf"

        # Open the pdf file
        if config.settings.open_pdf_viewer:
            execute_command(["xdg-open", str(destination_path)])
    else:
        logger.info("Dry run mode enabled. Skipping PDF generation.")
        logger.debug(f"Rendered template saved to: {LETTER_TMP_DIR / 'letter.typ'}")
        logger.debug(f"Output PDF would be saved to: {destination_path}")
