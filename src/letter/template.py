from pathlib import Path

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
from src.utils import compose_latex_command, config_logging, execute_command, latex_jinja_env, load_config

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

    template = latex_jinja_env.get_template("letter.tex.j2")

    # Render the template
    rendered_template = template.render(
        config=config,
        letter=frontmatter,
        content=content,
    )

    # Create output and tmp directory if they don't exist
    LETTER_OUT_DIR.mkdir(parents=True, exist_ok=True)
    LETTER_TMP_DIR.mkdir(parents=True, exist_ok=True)

    # Store tex file based on invoice number
    with (LETTER_TMP_DIR / "letter.tex").open("w") as f:
        f.write(rendered_template)

    # Only run the PDF generation command if not in dry run mode
    if not dry_run:
        # Run the generate_pdf command within a Podman container
        latex_command = compose_latex_command(LETTER_OUT_DIR, LETTER_TMP_DIR / "letter.tex", not verbose)

        # Execute the command to generate the PDF
        logger.debug(f"Running command: {latex_command}")
        execute_command(latex_command, exit_on_error=True, output_file=destination_path)

        # If example mode, copy the generated PDF to the example directory
        if example_mode:
            Path.rename(destination_path, EXAMPLE_DIR / "letter.example.pdf")
            destination_path = EXAMPLE_DIR / "letter.example.pdf"

        # Open the pdf file
        if config.settings.open_pdf_viewer:
            execute_command(["xdg-open", str(destination_path)])
    else:
        logger.info("Dry run mode enabled. Skipping PDF generation.")
        logger.debug(f"Rendered template saved to: {LETTER_TMP_DIR / 'letter.tex'}")
        logger.debug(f"Output PDF would be saved to: {destination_path}")
