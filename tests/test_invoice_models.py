"""Tests for invoice data models: Item calculations, Invoice totals, validation."""

import datetime as dt

import pytest
from pydantic import ValidationError

from invoice_toolkit.invoice.models.invoices import Invoice, Invoices, Item


class TestItem:
    def test_total_computed(self):
        item = Item(name="Service", quantity=3, unit="Stunde", price=50.0)
        assert item.total == 150.0

    def test_vat_computed_with_rate(self):
        item = Item(name="Service", quantity=2, unit="Stunde", price=100.0, vat_rate=19)
        assert item.total == 200.0
        assert item.vat_amount == 38.0
        assert item.gross_total == 238.0

    def test_vat_zero_when_no_rate(self):
        item = Item(name="Service", quantity=1, unit="Stück", price=10.0)
        assert item.vat_amount == 0.0
        assert item.gross_total == 10.0

    def test_vat_rate_7(self):
        item = Item(name="Cake", quantity=1, unit="Stück", price=3.50, vat_rate=7)
        # 3.50 * 7 / 100 = 0.245 → round(0.245, 2) = 0.24 (banker's rounding)
        assert item.vat_amount == 0.24
        assert item.gross_total == 3.74

    def test_invalid_unit_rejected(self):
        with pytest.raises(ValidationError):
            Item(name="Service", quantity=1, unit="Liter", price=10.0)

    def test_negative_price_rejected(self):
        with pytest.raises(ValidationError):
            Item(name="Service", quantity=1, unit="Stück", price=-5.0)

    def test_zero_quantity_rejected(self):
        with pytest.raises(ValidationError):
            Item(name="Service", quantity=0, unit="Stück", price=10.0)


class TestInvoice:
    def _make_item(self, price=50.0, quantity=1, vat_rate=None):
        return Item(name="Service", quantity=quantity, unit="Stunde", price=price, vat_rate=vat_rate)

    def test_total_computed(self):
        inv = Invoice(customer_id=10000, items=[self._make_item(price=30), self._make_item(price=20)])
        assert inv.total == 50.0

    def test_total_gross_with_vat(self):
        inv = Invoice(customer_id=10000, items=[self._make_item(price=100, vat_rate=19)])
        assert inv.total == 100.0
        assert inv.total_vat == 19.0
        assert inv.total_gross == 119.0

    def test_empty_items_rejected(self):
        with pytest.raises(ValueError, match="items must not be empty"):
            Invoice(customer_id=10000, items=[])

    def test_zero_total_rejected(self):
        with pytest.raises(ValueError, match="Total must be greater than 0"):
            Invoice(customer_id=10000, items=[self._make_item(price=0)])

    def test_date_default_is_today(self):
        inv = Invoice(customer_id=10000, items=[self._make_item()])
        assert inv.date == dt.date.today()

    def test_custom_date(self):
        inv = Invoice(customer_id=10000, date=dt.date(2025, 1, 15), items=[self._make_item()])
        assert inv.date == dt.date(2025, 1, 15)

    def test_invoice_number_pattern_valid(self):
        inv = Invoice(customer_id=10000, invoice_number="RE0001", items=[self._make_item()])
        assert inv.invoice_number == "RE0001"

    def test_invoice_number_5_digits_valid(self):
        inv = Invoice(customer_id=10000, invoice_number="RE10000", items=[self._make_item()])
        assert inv.invoice_number == "RE10000"

    def test_invalid_invoice_number_rejected(self):
        with pytest.raises(ValidationError):
            Invoice(customer_id=10000, invoice_number="INV001", items=[self._make_item()])

    def test_customer_id_below_minimum_rejected(self):
        with pytest.raises(ValidationError):
            Invoice(customer_id=999, items=[self._make_item()])

    def test_status_literals(self):
        for status in ["draft", "sent", "paid"]:
            inv = Invoice(customer_id=10000, status=status, items=[self._make_item()])
            assert inv.status == status

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            Invoice(customer_id=10000, status="cancelled", items=[self._make_item()])

    def test_multiple_items_different_vat_rates(self):
        items = [
            Item(name="A", quantity=1, unit="Stück", price=100.0, vat_rate=19),
            Item(name="B", quantity=1, unit="Stück", price=50.0, vat_rate=7),
        ]
        inv = Invoice(customer_id=10000, items=items)
        assert inv.total == 150.0
        assert inv.total_vat == pytest.approx(22.5)
        assert inv.total_gross == pytest.approx(172.5)


class TestInvoices:
    def test_invoices_list(self):
        item = Item(name="Service", quantity=1, unit="Stunde", price=50.0)
        invs = Invoices(invoices=[Invoice(customer_id=10000, items=[item])])
        assert len(invs.invoices) == 1
