"""CLI entry point for invoice and letter generation."""

from fire import Fire

from invoice_toolkit.invoice.template import create_invoices
from invoice_toolkit.invoice.utils import print_customer
from invoice_toolkit.letter.template import create_letter
from invoice_toolkit.utils import generate_schema


def main():
    """CLI entry point."""
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


if __name__ == "__main__":
    main()
