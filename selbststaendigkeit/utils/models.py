import tomllib
from pathlib import Path

import yaml

from selbststaendigkeit.models import Config, Customer, Invoice


def load_config(file: Path) -> Config:
    """Load config file.

    Parameters
    ----------
    file : Path
        Path to config file.

    Returns
    -------
    Config
        Config object.
    """
    with Path.open(file, "rb") as f:
        file = tomllib.load(f)
        config = Config(**file)
    return config


def load_customer(file: Path, id: str | int) -> Customer:
    """Load customer file.

    This function loads the customer file, filters the customer by id and
    returns the first customer object that matches the id.

    Parameters
    ----------
    file : Path
        Path to customer file.
    id : str | int

    Returns
    -------
    Customer
        Customer object.
    """
    with Path.open(file, "rb") as f:
        file = yaml.safe_load(f)
        customers = [Customer(**c) for c in file["customers"]]

    # Validate that the customer ids are unique
    customer_ids = [c.id for c in customers]
    if len(customer_ids) != len(set(customer_ids)):
        raise ValueError("Customer ids must be unique.")

    # Filter the customer by id
    customers = [c for c in customers if c.id == id]
    return customers[0]


def load_invoice(file: Path) -> Invoice:
    """Load invoice file.

    Parameters
    ----------
    file : Path
        Path to invoice file.

    Returns
    -------
    dict
        Invoice dictionary.
    """
    with Path.open(file, "rb") as f:
        file = yaml.safe_load(f)
        invoice = Invoice(**file)
    return invoice
