"""Utilities for loading and selecting invoices and customers."""

import csv
import logging
from typing import TYPE_CHECKING

import yaml

from invoice_toolkit.invoice.models import Customer, Invoices
from invoice_toolkit.settings import DATA_DIR

if TYPE_CHECKING:
    from pathlib import Path

    from invoice_toolkit.invoice.models.invoices import Invoice

logger = logging.getLogger(__name__)


def confirm(prompt: str, default: bool = True) -> bool:
    """Confirm prompt."""
    valid_responses = {"yes": True, "y": True, "no": False, "n": False}
    response_prompt = f"{prompt} [Y/n] " if default else f"{prompt} [y/N] "

    while True:
        choice = input(response_prompt).lower()
        if default is not None and choice == "":
            return default
        elif choice in valid_responses:
            return valid_responses[choice]
        else:
            print("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")


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
    except Exception as e:
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


def _parse_selection(raw: str, max_index: int) -> list[int] | None:
    """Parse a comma-separated selection string with range support.

    Accepts formats like "0,2-4,6". Returns deduplicated indices in input order,
    filtering out non-numeric or out-of-bounds values. Returns None if nothing valid.
    """
    seen: set[int] = set()
    result: list[int] = []

    for raw_part in raw.split(","):
        part = raw_part.strip()
        if "-" in part:
            bounds = part.split("-", 1)
            try:
                start, end = int(bounds[0].strip()), int(bounds[1].strip())
            except ValueError:
                continue
            for i in range(start, end + 1):
                if 0 <= i <= max_index and i not in seen:
                    seen.add(i)
                    result.append(i)
        else:
            try:
                i = int(part)
            except ValueError:
                continue
            if 0 <= i <= max_index and i not in seen:
                seen.add(i)
                result.append(i)

    return result if result else None


def select_invoice(invoices: list[Invoice], customer_file: Path) -> list[Invoice]:
    """Interactively select draft invoices to generate.

    - 0 drafts: returns []
    - 1 draft: returns it directly (no prompt)
    - Multiple drafts: displays a numbered list and prompts for all or comma-separated selection
    """
    drafts = [inv for inv in invoices if inv.status == "draft"]

    if not drafts:
        return []

    if len(drafts) == 1:
        return drafts

    # Sort by date descending (newest first)
    drafts.sort(key=lambda inv: inv.date, reverse=True)

    # Load customer names for display
    customers = load_customers(customer_file)

    print("Available draft invoices:")
    print("-" * 60)
    for i, inv in enumerate(drafts):
        name = customers[inv.customer_id].address.name if inv.customer_id in customers else str(inv.customer_id)
        print(f"  {i}: {name} - {inv.date} - {inv.total:.2f} EUR")
    print("-" * 60)

    mode = input("Generate all or select specific invoices? [a/s] (default: s): ").strip().lower()

    if mode == "a":
        return drafts

    raw = input("Which invoices should be generated? (e.g. 0,2-4,6): ").strip()
    indices = _parse_selection(raw, len(drafts) - 1)

    if indices is None:
        logger.warning(f"Invalid selection: '{raw}'. No invoices selected.")
        return []

    return [drafts[i] for i in indices]


def load_invoice(file: Path) -> Invoices:
    """Load invoice file."""
    try:
        with file.open("rb") as f:
            parsed_file = yaml.safe_load(f)
            invoices = Invoices(**parsed_file)
        return invoices
    except (yaml.YAMLError, ValueError, TypeError) as e:
        raise ValueError(f"Failed to load invoices from {file}: {e}") from e


def print_customer(file: Path = DATA_DIR / "customer.csv") -> None:
    """Print customer-to-id mapping."""
    with file.open("r", encoding="utf-8-sig") as f:
        parsed_file = csv.DictReader(f)
        for customer in parsed_file:
            print(f"{customer['name']}: {customer['customer_id']}")
