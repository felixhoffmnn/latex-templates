import csv
from pathlib import Path

import yaml

from src.invoice.models import Customer, Invoices
from src.settings import INVOICE_DIR


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


def load_customer(file: Path, customer_id: str | int) -> Customer:
    """Load customer file."""
    with file.open("r", encoding="utf-8-sig") as f:
        parsed_file = csv.DictReader(f)
        customers = [
            Customer(**{k: v if v else None for k, v in customer.items()}) for customer in parsed_file if customer
        ]

    # Validate that the customer ids are unique
    customer_ids = [c.customer_id for c in customers]
    if len(customer_ids) != len(set(customer_ids)):
        raise ValueError("Customer ids must be unique.")

    # Filter the customers by id
    matching_customers = [c for c in customers if c.customer_id == customer_id]

    if not matching_customers:
        raise ValueError(f"No customer found with id {customer_id}")

    if len(matching_customers) > 1:
        raise ValueError(f"Multiple customers found with id {customer_id}")

    return matching_customers[0]


def load_invoice(file: Path) -> Invoices:
    """Load invoice file."""
    with file.open("rb") as f:
        parsed_file = yaml.safe_load(f)
        invoices = Invoices(**parsed_file)
    return invoices


def print_customer(file: Path = INVOICE_DIR / "customer.csv") -> None:
    """Print customer-to-id mapping."""
    with file.open("r", encoding="utf-8-sig") as f:
        parsed_file = csv.DictReader(f)
        for customer in parsed_file:
            print(f"{customer['name']}: {customer['customer_id']}")
