import subprocess
from pathlib import Path

from loguru import logger

from src.letter.utils import load_letter
from src.settings import (
    CONFIG_DEFAULT_FILE,
    CONFIG_EXAMPLE_FILE,
    LETTER_DEFAULT_FILE,
    LETTER_EXAMPLE_FILE,
    OUT_DIR,
    TMP_DIR,
)
from src.utils import compose_latex_command, latex_jinja_env, load_config

LETTER_OUTPUT_DIR = OUT_DIR / "letter"
LETTER_TMP_DIR = TMP_DIR / "letter"


def create_letter(
    letter_file: Path | str | None = None,
    config_file: Path | str | None = None,
    latex_quiet: bool = True,
):
    """Create a letter.

    This function will create a letter based on the given config and letter files.
    """
    if (letter_file or config_file) is None:
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
    LETTER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LETTER_TMP_DIR.mkdir(parents=True, exist_ok=True)

    # Store tex file based on invoice number
    with (LETTER_TMP_DIR / "letter.tex").open("w") as f:
        f.write(rendered_template)

    # Run the generate_pdf command within a Podman container
    latex_command = compose_latex_command(LETTER_OUTPUT_DIR, LETTER_TMP_DIR / "letter.tex", latex_quiet)

    logger.debug(f"Running command: {latex_command}")

    try:
        subprocess.run(latex_command, check=True)
        logger.success(f"PDF generated successfully at: {LETTER_OUTPUT_DIR / 'letter.pdf'}")
    except subprocess.CalledProcessError as e:
        logger.error(f"PDF generation failed: {e}")

    # Open the pdf file
    if config.settings.open_pdf_viewer:
        try:
            subprocess.run(
                ["xdg-open", (LETTER_OUTPUT_DIR / "letter.pdf").absolute()],
                check=True,
            )
            logger.success("PDF opened successfully.")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"PDF opening failed: {e}")
