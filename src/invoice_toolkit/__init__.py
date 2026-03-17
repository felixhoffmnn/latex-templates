"""Invoice Toolkit — generate invoices and letters from templates."""

from invoice_toolkit.invoice.template import InvoiceResult, create_invoice, create_invoices
from invoice_toolkit.letter.template import create_letter
from invoice_toolkit.models import Config
from invoice_toolkit.settings import ProjectPaths
from invoice_toolkit.utils import create_jinja_env, load_yaml_model

__all__ = [
    "Config",
    "InvoiceResult",
    "ProjectPaths",
    "create_invoice",
    "create_invoices",
    "create_jinja_env",
    "create_letter",
    "load_yaml_model",
]
