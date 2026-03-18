"""Typer CLI entry point for invoice and letter generation."""

from __future__ import annotations

import logging

import typer

from invoice_toolkit.cli.invoice import invoice_command, print_customer_command
from invoice_toolkit.cli.letter import letter_command
from invoice_toolkit.cli.schemas import schemas_command

app = typer.Typer(help="Invoice Toolkit — generate invoices and letters from templates.")


@app.callback()
def _config_logging():
    """Configure the logging level based on the debug flag."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


app.command("invoice")(invoice_command)
app.command("letter")(letter_command)
app.command("print-customer")(print_customer_command)
app.command("schemas")(schemas_command)
