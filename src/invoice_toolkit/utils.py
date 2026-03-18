"""Shared utilities for configuration and Jinja environment."""

import logging
import shutil
from importlib.resources import files
from pathlib import Path

import jinja2
import typst
import yaml
from pydantic import BaseModel

logger = logging.getLogger("invoice_toolkit")


def bundled_template_dir() -> Path:
    """Return the path to the templates bundled inside the installed package."""
    return Path(str(files("invoice_toolkit").joinpath("templates")))


def _currency_filter(value, locale="de"):
    if locale == "de":
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{value:.2f}"


def create_jinja_env(template_dir: Path) -> jinja2.Environment:
    """Create a Jinja2 environment rooted at *template_dir*."""
    env = jinja2.Environment(
        trim_blocks=True,
        autoescape=False,
        loader=jinja2.FileSystemLoader(str(template_dir)),
    )
    env.filters["currency"] = _currency_filter
    return env


def render_typst_to_pdf(rendered: str, typ_path: Path, pdf_path: Path, project_root: Path, template_dir: Path) -> None:
    """Write a rendered Typst source to *typ_path* and compile it to *pdf_path*.

    Copies ``base.typ`` from *template_dir* next to *typ_path* so the
    ``#import "base.typ"`` directive in the rendered template resolves correctly.
    """
    try:
        with typ_path.open("w") as f:
            f.write(rendered)
    except OSError as e:
        raise OSError(f"Failed to write Typst file {typ_path}: {e}") from e

    shutil.copy2(template_dir / "base.typ", typ_path.parent / "base.typ")

    try:
        typst.compile(str(typ_path), output=str(pdf_path), root=str(project_root))
    except Exception as e:
        raise RuntimeError(f"Typst compilation failed for {typ_path}: {e}") from e


def load_yaml_model[T: BaseModel](file: Path, model_cls: type[T]) -> T:
    """Load a YAML file and construct a Pydantic model.

    Raises ValueError on parse or validation failure.
    """
    try:
        with file.open("rb") as f:
            parsed_file = yaml.safe_load(f)
            return model_cls(**parsed_file)
    except (OSError, yaml.YAMLError, ValueError, TypeError) as e:
        raise ValueError(f"Failed to load {model_cls.__name__} from {file}: {e}") from e
