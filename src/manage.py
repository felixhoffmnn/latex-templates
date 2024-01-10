from fire import Fire

from src.invoice.template import create_invoices
from src.invoice.utils import print_customer
from src.letter.template import create_letter
from src.utils import generate_schema

if __name__ == "__main__":
    Fire(
        {
            # Create one or more invoices
            "invoice": create_invoices,
            # Create a letter
            "letter": create_letter,
            # Print customer information
            "print_customer": print_customer,
            # Generate JSON schema for the invoice and letter templates
            "schemas": generate_schema,
        }
    )
