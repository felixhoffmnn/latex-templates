"""Generate JSON schemas for pydantic models."""

import json
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from invoice_toolkit.invoice.models import Customer, Invoices
from invoice_toolkit.models import Config

if TYPE_CHECKING:
    from pydantic import BaseModel

logger = logging.getLogger(__name__)


def schemas_command():
    """Generate JSON schemas for pydantic models."""
    schema_dir = Path("schema")
    schemas: list[type[BaseModel]] = [Config, Invoices, Customer]

    try:
        schema_dir.mkdir(exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create schema directory {schema_dir}: {e}")
        sys.exit(1)

    for schema in schemas:
        try:
            with (schema_dir / f"{schema.__name__.lower()}.json").open("w") as f:
                json.dump(schema.model_json_schema(), f, indent=2)
                f.write("\n")
        except OSError as e:
            logger.error(f"Failed to write schema for {schema.__name__}: {e}")
            sys.exit(1)
        logger.info(f"Generated schema for {schema.__name__}")
