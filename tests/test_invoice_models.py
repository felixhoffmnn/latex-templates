import datetime as dt

import pytest
from pydantic import ValidationError

from invoice_toolkit.invoice.models.invoices import Invoice, Item


def item(**overrides):
    return Item(**({"name": "Service", "quantity": 1, "unit": "Stunde", "price": 50.0} | overrides))


def test_item_totals_and_vat():
    standard = item(quantity=2, price=100.0, vat_rate=19)
    reduced = item(unit="Stück", price=3.5, vat_rate=7)
    zero = item(price=10.0)

    assert (standard.total, standard.vat_amount, standard.gross_total) == (200.0, 38.0, 238.0)
    assert (reduced.vat_amount, reduced.gross_total) == (0.24, 3.74)
    assert (zero.vat_amount, zero.gross_total) == (0.0, 10.0)


@pytest.mark.parametrize("overrides", [{"unit": "Liter"}, {"price": -5.0}, {"quantity": 0}])
def test_item_rejects_invalid_business_values(overrides):
    with pytest.raises(ValidationError):
        item(**overrides)


def test_invoice_totals_and_defaults():
    invoice = Invoice(
        customer_id=10000,
        items=[item(price=100.0, vat_rate=19), item(price=50.0, vat_rate=7)],
    )
    assert invoice.date == dt.date.today()  # noqa: DTZ011 - matches the model's local-date default
    assert (invoice.total, invoice.total_vat, invoice.total_gross) == (150.0, 22.5, 172.5)


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"items": []}, ValueError),
        ({"items": [item(price=0)]}, ValueError),
        ({"customer_id": 999}, ValidationError),
        ({"invoice_number": "INV001"}, ValidationError),
        ({"status": "cancelled"}, ValidationError),
    ],
)
def test_invoice_rejects_invalid_business_values(kwargs, error):
    with pytest.raises(error):
        Invoice(customer_id=kwargs.pop("customer_id", 10000), items=kwargs.pop("items", [item()]), **kwargs)
