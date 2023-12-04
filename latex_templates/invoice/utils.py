import csv
import tomllib
from pathlib import Path

import yaml

from latex_templates.invoice.models import Config, Customer, Invoice


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


def load_config(file: Path) -> Config:
    """Load config file."""
    with file.open("rb") as f:
        parsed_file = tomllib.load(f)
        config = Config(**parsed_file)
    return config


def load_customer(file: Path, customer_id: str | int) -> Customer:
    """Load customer file."""
    with file.open("r", encoding="utf-8-sig") as f:
        parsed_file = csv.DictReader(f)
        customers = [Customer(**customer) for customer in parsed_file if customer]

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


def load_invoice(file: Path) -> list[Invoice]:
    """Load invoice file."""
    with file.open("rb") as f:
        parsed_file = yaml.safe_load(f)
        invoices = [Invoice(**invoice) for invoice in parsed_file]
    return invoices
