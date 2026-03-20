"""Shared utilities for configuration and template compilation."""

import json
import logging
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING

import typst
import yaml
from pydantic import BaseModel

if TYPE_CHECKING:
    from invoice_toolkit.models import Sender

logger = logging.getLogger("invoice_toolkit")


def bundled_template_dir() -> Path:
    """Return the path to the templates bundled inside the installed package."""
    return Path(str(files("invoice_toolkit").joinpath("templates")))


def compile_template(template_name: str, data: dict, pdf_path: Path, template_dir: Path) -> None:
    """Compile a Typst template to PDF, passing *data* as JSON via ``sys.inputs``."""
    try:
        typst.compile(
            str(template_dir / template_name),
            output=str(pdf_path),
            root=str(template_dir),
            sys_inputs={"data": json.dumps(data, ensure_ascii=False)},
        )
    except Exception as e:
        raise RuntimeError(f"Typst compilation failed for {template_name}: {e}") from e


def build_sender_data(sender: Sender) -> dict:
    """Serialize a Sender model into the dict expected by Typst templates.

    Returns a nested dict with top-level ``sender``, ``tax``, and ``bank``
    keys, each mapping to a dict of plain string values (no Pydantic special
    types).
    """
    phone = str(sender.phone).replace("tel:", "").replace("-", " ")
    return {
        "sender": {
            "name": sender.address.name,
            "street": sender.address.street,
            "zip": sender.address.zip,
            "city": sender.address.city,
            "phone": phone,
            "email": str(sender.email),
            "website": str(sender.website),
        },
        "tax": {
            "office": sender.tax.office,
            "number": sender.tax.number,
        },
        "bank": {
            "name": sender.bank.name,
            "iban": sender.bank.iban,
            "bic": sender.bank.bic,
        },
    }


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
