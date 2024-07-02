from fire import Fire

from latex_templates.invoice.template import create_invoices
from latex_templates.utils import generate_schema

if __name__ == "__main__":
    Fire({"invoice": create_invoices, "schemas": generate_schema})
