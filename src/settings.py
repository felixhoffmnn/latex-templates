import os
from pathlib import Path

# Default directories
DATA_DIR = Path("data")
INVOICE_DIR = Path(os.getenv("INVOICE_DIR", DATA_DIR))
EXAMPLE_DIR = Path("example")
OUT_DIR = Path("out")
TMP_DIR = Path("tmp")

# Example file paths
CONFIG_EXAMPLE_FILE = EXAMPLE_DIR / "config.example.yml"
INVOICE_EXAMPLE_FILE = EXAMPLE_DIR / "invoices.example.yml"
INVOICE_CUSTOMER_EXAMPLE_FILE = EXAMPLE_DIR / "customer.example.csv"
LETTER_EXAMPLE_FILE = EXAMPLE_DIR / "letter.example.md"

# Default file paths
CONFIG_DEFAULT_FILE = Path("config.toml")
INVOICE_HISTORY_FILE = INVOICE_DIR / "invoice.csv"
INVOICE_CUSTOMER_FILE = INVOICE_DIR / "customer.csv"
LETTER_DEFAULT_FILE = DATA_DIR / "letter.yml"
