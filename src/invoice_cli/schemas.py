"""Generate JSON schemas for pydantic models."""

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from invoice_toolkit.invoice.models import Customer, Invoices
from invoice_toolkit.models import Config

if TYPE_CHECKING:
    from pydantic import BaseModel

logger = logging.getLogger(__name__)


def schemas_command():
    """Generate JSON schemas for pydantic models."""
    logger = logging.getLogger("schemas_command")

    schema_dir = Path("schema")
    schemas: list[type[BaseModel]] = [Config, Invoices, Customer]

    schema_dir.mkdir(exist_ok=True)

    for schema in schemas:
        with (schema_dir / f"{schema.__name__.lower()}.json").open("w") as f:
            json.dump(schema.model_json_schema(), f, indent=2)
        logger.info(f"Generated schema for {schema.__name__}")
