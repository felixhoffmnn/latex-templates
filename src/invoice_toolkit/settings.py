import os
from pathlib import Path

# Default directories
DATA_DIR = Path("data")
INVOICE_DIR = Path(os.getenv("INVOICE_DIR", DATA_DIR))
OUT_DIR = Path("out")
TMP_DIR = Path("tmp")

# Default file paths
CONFIG_DEFAULT_FILE = Path("config.yml")
INVOICE_HISTORY_FILE = INVOICE_DIR / "invoice.csv"
INVOICE_CUSTOMER_FILE = INVOICE_DIR / "customer.csv"
LETTER_DEFAULT_FILE = DATA_DIR / "letter.yml"
