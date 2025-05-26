from fire import Fire

from src.invoice.template import create_invoices
from src.invoice.utils import print_customer
from src.utils import generate_schema

if __name__ == "__main__":
    Fire({"invoice": create_invoices, "print_customer": print_customer, "schemas": generate_schema})
