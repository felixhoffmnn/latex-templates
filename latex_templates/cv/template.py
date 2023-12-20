import subprocess
from pathlib import Path

from loguru import logger

from latex_templates.cv import utils
from latex_templates.utils import compose_latex_command, latex_jinja_env

DATA_DIR = Path("data")
OUTPUT_DIR = Path("out/cv")
TMP_DIR = Path("tmp/cv")


def create_cv(config_file: Path = DATA_DIR / "curriculum_vitae.yml", latex_quiet: bool = True):
    """Create CV."""
    config = utils.load_cv(config_file)

    # Load and configure the template
    template = latex_jinja_env.get_template("cv.tex.j2")

    # Render the template
    rendered_template = template.render(
        person=config.person,
        social=config.social,
        engagement=config.engagement,
        skills=config.skills,
        education=config.education,
        experience=config.experience,
    )

    # Create output and tmp directory if they don't exist
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    # Store tex file based on invoice number
    with (TMP_DIR / "cv.tex").open("w") as f:
        f.write(rendered_template)

    # Run the generate_pdf command within a Podman container
    latex_command = compose_latex_command(OUTPUT_DIR, TMP_DIR / "cv.tex", latex_quiet)

    try:
        subprocess.run(latex_command, check=True)
        logger.success(f"PDF generated successfully at: {OUTPUT_DIR / 'cv.pdf'}")
    except subprocess.CalledProcessError as e:
        logger.error(f"PDF generation failed: {e}")
