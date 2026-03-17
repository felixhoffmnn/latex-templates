"""Shared test factories for invoice-toolkit."""

import datetime as dt

from invoice_toolkit.invoice.models.customer import Customer
from invoice_toolkit.invoice.models.invoices import Invoice, Item
from invoice_toolkit.models import Address, Bank, Config, Sender, Tax
from invoice_toolkit.models import Invoice as InvoiceConfig


def make_item(price: float = 50.0, quantity: int = 1, vat_rate: int | None = None) -> Item:
    return Item(name="Service", quantity=quantity, unit="Stunde", price=price, vat_rate=vat_rate)


def make_invoice(**overrides) -> Invoice:
    defaults: dict = {
        "customer_id": 10000,
        "invoice_id": 1,
        "invoice_number": "RE0001",
        "date": dt.date(2025, 6, 15),
        "due_date": dt.date(2025, 7, 15),
        "items": [make_item()],
    }
    defaults.update(overrides)
    return Invoice(**defaults)


def make_config(**overrides) -> Config:
    defaults: dict = {
        "sender": Sender(
            address=Address(name="Sender Name", street="St 1", zip="12345", city="Berlin"),
            email="sender@example.com",
            website="https://example.com",  # type: ignore[invalid-argument-type]
            phone="+49 176 12345678",  # type: ignore[invalid-argument-type]
            tax=Tax(number="12 345 6789 0", office="Berlin"),
            bank=Bank(name="Test Bank", iban="DE89370400440532013000", bic="AAAAAAA1BBB"),
        ),
        "invoice": InvoiceConfig(VAT=0, due_days=14),
    }
    defaults.update(overrides)
    return Config(**defaults)


def make_customer(**overrides) -> Customer:
    defaults: dict = {
        "customer_id": 10000,
        "name": "Kunde Name",
        "email": "kunde@example.com",
        "phone": "+49 176 87654321",
        "street": "Kundenstr. 1",
        "zip": "54321",
        "city": "Munich",
    }
    defaults.update(overrides)
    return Customer(**defaults)
