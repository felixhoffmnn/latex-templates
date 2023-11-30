import tomllib
from pathlib import Path

import yaml

from latex_templates.invoice.models import Config, Customer, Invoices


def confirm(prompt: str, default: bool = True) -> bool:
    """Confirm prompt.

    Parameters
    ----------
    prompt : str
        Prompt to confirm.
    default : bool, optional
        Default value, by default True

    Returns
    -------
    bool
        True if confirmed, False otherwise.
    """
    valid = {"yes": True, "y": True, "no": False, "n": False}
    if default is None:
        prompt = f"{prompt} [y/n] "
    elif default:
        prompt = f"{prompt} [Y/n] "
    else:
        prompt = f"{prompt} [y/N] "
    while True:
        choice = input(prompt).lower()
        if default is not None and choice == "":
            return default
        elif choice in valid:
            return valid[choice]
        else:
            print("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")


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
        parsed_file = tomllib.load(f)
        config = Config(**parsed_file)
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
        parsed_file = yaml.safe_load(f)
        customers = [Customer(**c) for c in parsed_file["customers"]]

    # Validate that the customer ids are unique
    customer_ids = [c.id for c in customers]
    if len(customer_ids) != len(set(customer_ids)):
        raise ValueError("Customer ids must be unique.")

    # Filter the customer by id
    customers = [c for c in customers if c.id == id]
    return customers[0]


def load_invoice(file: Path) -> Invoices:
    """Load invoice file.

    Parameters
    ----------
    file : Path
        Path to invoice file.

    Returns
    -------
    dict
        Invoices object.
    """
    with Path.open(file, "rb") as f:
        parsed_file = yaml.safe_load(f)
        invoices = Invoices(**parsed_file)
    return invoices
