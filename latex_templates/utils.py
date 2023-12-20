import os
import tomllib
from pathlib import Path

import jinja2

from latex_templates.models import Config

latex_jinja_env = jinja2.Environment(
    block_start_string="((*",
    block_end_string="*))",
    variable_start_string="(((",
    variable_end_string=")))",
    comment_start_string="((=",
    comment_end_string="=))",
    trim_blocks=True,
    autoescape=False,
    loader=jinja2.FileSystemLoader("template"),
)


def load_config(file: Path) -> Config:
    """Load config file."""
    with file.open("rb") as f:
        parsed_file = tomllib.load(f)
        config = Config(**parsed_file)
    return config


def compose_latex_command(out_dir: Path, tex_file: Path, quiet: bool):
    """Compose the latex command.

    This function will compose the latex command to generate a pdf from a tex file.
    The generation will take place within a container
    """
    return [
        os.environ.get("CONTAINER_RUNTIME", "podman"),
        "run",
        "--rm",
        "-it",
        "-v",
        f"{Path.cwd()}:/workdir:z",
        "-w",
        "/workdir",
        "--userns",
        f"keep-id:uid={os.getuid()},gid={os.getgid()}",
        "texlive/texlive:latest-full",
        "latexmk",
        f"-output-directory={out_dir}",
        "-pdf",
        "-quiet" if quiet else "-verbose",
        str(tex_file),
    ]
