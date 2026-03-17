"""Utilities for loading invoices and customers."""

import csv
import logging
from typing import TYPE_CHECKING

import yaml

from invoice_toolkit.invoice.models import Customer, Invoices

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


def load_customers(file: Path) -> dict[int, Customer]:
    """Load all customers from a CSV file.

    Returns a dict keyed by customer_id.
    """
    try:
        with file.open("r", encoding="utf-8-sig") as f:
            parsed_file = csv.DictReader(f)
            customers = [
                Customer(**{k: v if v else None for k, v in customer.items()}) for customer in parsed_file if customer
            ]
    except (csv.Error, ValueError, TypeError, OSError) as e:
        raise ValueError(f"Failed to load customers from {file}: {e}") from e

    # Validate that the customer ids are unique
    customer_ids = [c.customer_id for c in customers]
    if len(customer_ids) != len(set(customer_ids)):
        raise ValueError(f"Duplicate customer IDs found in {file}.")

    return {c.customer_id: c for c in customers}


def load_customer(file: Path, customer_id: str | int) -> Customer:
    """Load a single customer by id from a CSV file."""
    customers = load_customers(file)
    customer_id = int(customer_id)

    if customer_id not in customers:
        raise ValueError(f"No customer found with id {customer_id} in {file}")

    return customers[customer_id]


def load_invoice(file: Path) -> Invoices:
    """Load invoice file."""
    try:
        with file.open("rb") as f:
            parsed_file = yaml.safe_load(f)
            invoices = Invoices(**parsed_file)
        return invoices
    except (yaml.YAMLError, ValueError, TypeError) as e:
        raise ValueError(f"Failed to load invoices from {file}: {e}") from e
