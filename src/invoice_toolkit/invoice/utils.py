"""Utilities for loading invoices and customers."""

import csv
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from invoice_toolkit.invoice.models import Customer

if TYPE_CHECKING:
    from pathlib import Path

    from invoice_toolkit.invoice.models.invoices import Item

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VatGroup:
    """Aggregated basis and tax amount for a single VAT rate."""

    basis: float
    amount: float


def group_items_by_vat(items: list[Item]) -> dict[int, VatGroup]:
    """Group invoice items by VAT rate and sum their basis/amount.

    Raises ValueError if any item has no VAT rate.
    """
    groups: dict[int, VatGroup] = {}
    for item in items:
        rate = item.vat_rate
        if rate is None:
            raise ValueError(f"Item '{item.name}' has no VAT rate")
        prev = groups.get(rate, VatGroup(basis=0.0, amount=0.0))
        groups[rate] = VatGroup(
            basis=round(prev.basis + item.total, 2),
            amount=round(prev.amount + item.vat_amount, 2),
        )
    return groups


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
