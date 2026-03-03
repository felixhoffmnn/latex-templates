import os
from pathlib import Path

# Project root (resolved once at import time so later cwd changes don't break paths)
PROJECT_ROOT = Path.cwd().resolve()

# Default directories
DATA_DIR = PROJECT_ROOT / "data"
INVOICE_DIR = Path(os.getenv("INVOICE_DIR", str(DATA_DIR)))
OUT_DIR = PROJECT_ROOT / "out"
TMP_DIR = PROJECT_ROOT / "tmp"
TEMPLATE_DIR = PROJECT_ROOT / "template"

# Default file paths
CONFIG_DEFAULT_FILE = PROJECT_ROOT / "config.yml"
INVOICE_HISTORY_FILE = INVOICE_DIR / "invoice.csv"
INVOICE_CUSTOMER_FILE = INVOICE_DIR / "customer.csv"
LETTER_DEFAULT_FILE = DATA_DIR / "letter.yml"
