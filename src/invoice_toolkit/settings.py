"""Global path constants and directory configuration."""

import os
from pathlib import Path

# Project root (resolved once at import time so later cwd changes don't break paths)
PROJECT_ROOT = Path.cwd().resolve()

# Default directories
DATA_DIR = Path(os.getenv("DATA_DIR", str(PROJECT_ROOT / "data")))
OUT_DIR = PROJECT_ROOT / "out"
TMP_DIR = PROJECT_ROOT / "tmp"
TEMPLATE_DIR = PROJECT_ROOT / "template"

# Default file paths (CSV)
INVOICE_HISTORY_FILE = DATA_DIR / "invoice.csv"
INVOICE_CUSTOMER_FILE = DATA_DIR / "customer.csv"


def _find_yaml(directory: Path, stem: str) -> Path | None:
    """Return the first existing YAML file matching *stem* (.yml then .yaml)."""
    for ext in (".yml", ".yaml"):
        candidate = directory / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def resolve_invoices_path() -> Path:
    """Resolve invoices file path: INVOICES_PATH env → DATA_DIR/invoices.{yml,yaml}."""
    env = os.getenv("INVOICES_PATH")
    if env:
        return Path(env)
    found = _find_yaml(DATA_DIR, "invoices")
    if found:
        return found
    return DATA_DIR / "invoices.yaml"


def resolve_config_path() -> Path:
    """Resolve config file path: CONFIG_PATH env → DATA_DIR/config.{yml,yaml} → root config.{yml,yaml}."""
    env = os.getenv("CONFIG_PATH")
    if env:
        return Path(env)
    found = _find_yaml(DATA_DIR, "config")
    if found:
        return found
    found = _find_yaml(PROJECT_ROOT, "config")
    if found:
        return found
    # Return root default so validate_paths gives a clear error
    return PROJECT_ROOT / "config.yaml"
