import os
from pathlib import Path

DATA_DIR = Path("data")
INVOICE_DIR = Path(os.getenv("INVOICE_DIR", DATA_DIR))
EXAMPLE_DIR = Path("example")
OUTPUT_DIR = Path("out/invoices")
TMP_DIR = Path("tmp/invoices")
