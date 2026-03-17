"""Typer CLI entry point for invoice and letter generation."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import typer

from invoice_cli.invoice import invoice_command, print_customer_command
from invoice_cli.letter import letter_command
from invoice_toolkit.invoice.models import Customer, Invoices
from invoice_toolkit.models import Config

if TYPE_CHECKING:
    from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = typer.Typer(help="Invoice Toolkit — generate invoices and letters from templates.")
app.command("invoice")(invoice_command)
app.command("letter")(letter_command)
app.command("print-customer")(print_customer_command)


@app.command("schemas")
def schemas_command():
    """Generate JSON schemas for pydantic models."""
    schema_dir = Path("schema")
    schemas: list[type[BaseModel]] = [Config, Invoices, Customer]

    schema_dir.mkdir(exist_ok=True)

    for schema in schemas:
        with (schema_dir / f"{schema.__name__.lower()}.json").open("w") as f:
            json.dump(schema.model_json_schema(), f, indent=2)
        logger.info(f"Generated schema for {schema.__name__}")


def main():
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
