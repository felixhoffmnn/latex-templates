"""Tests for VAT resolution and VAT context preparation."""

import pytest

from invoice_toolkit.invoice.models.invoices import Invoice, Item
from invoice_toolkit.invoice.template import _prepare_vat_context, _resolve_vat


def _make_item(price=100.0, quantity=1, vat_rate=None):
    return Item(name="Service", quantity=quantity, unit="Stunde", price=price, vat_rate=vat_rate)


def _make_invoice(items, **kwargs):
    return Invoice(customer_id=10000, items=items, **kwargs)


class TestResolveVat:
    def test_vat_exempt_forces_zero(self):
        items = [_make_item(vat_rate=19), _make_item(vat_rate=7)]
        inv = _make_invoice(items)

        _resolve_vat(inv, vat_exempt=True, default_vat_rate=19)

        for item in inv.items:
            assert item.vat_rate == 0
            assert item.vat_amount == 0.0
        assert inv.total_vat == 0.0
        assert inv.total_gross == inv.total

    def test_default_rate_fills_none(self):
        items = [_make_item(vat_rate=None), _make_item(vat_rate=7)]
        inv = _make_invoice(items)

        _resolve_vat(inv, vat_exempt=False, default_vat_rate=19)

        assert inv.items[0].vat_rate == 19
        assert inv.items[1].vat_rate == 7  # explicit rate preserved

    def test_explicit_zero_preserved(self):
        items = [_make_item(vat_rate=0)]
        inv = _make_invoice(items)

        _resolve_vat(inv, vat_exempt=False, default_vat_rate=19)

        assert inv.items[0].vat_rate == 0
        assert inv.items[0].vat_amount == 0.0

    def test_amounts_recomputed(self):
        items = [_make_item(price=100, vat_rate=None)]
        inv = _make_invoice(items)

        _resolve_vat(inv, vat_exempt=False, default_vat_rate=19)

        assert inv.items[0].vat_amount == 19.0
        assert inv.items[0].gross_total == 119.0
        assert inv.total_vat == 19.0
        assert inv.total_gross == 119.0

    def test_mixed_rates(self):
        items = [
            _make_item(price=100, vat_rate=19),
            _make_item(price=50, vat_rate=7),
        ]
        inv = _make_invoice(items)

        _resolve_vat(inv, vat_exempt=False, default_vat_rate=19)

        assert inv.total == 150.0
        assert inv.total_vat == pytest.approx(22.5)
        assert inv.total_gross == pytest.approx(172.5)


class TestPrepareVatContext:
    def test_vat_exempt_context(self):
        items = [_make_item(vat_rate=0)]
        inv = _make_invoice(items)
        _resolve_vat(inv, vat_exempt=True, default_vat_rate=0)

        ctx = _prepare_vat_context(inv, vat_exempt=True)

        assert ctx["has_vat"] is False
        assert ctx["vat_groups"] == {}
        assert ctx["display_total"] == inv.total

    def test_vat_context_with_rates(self):
        items = [
            _make_item(price=100, vat_rate=19),
            _make_item(price=50, vat_rate=7),
        ]
        inv = _make_invoice(items)
        _resolve_vat(inv, vat_exempt=False, default_vat_rate=19)

        ctx = _prepare_vat_context(inv, vat_exempt=False)

        assert ctx["has_vat"] is True
        assert 19 in ctx["vat_groups"]
        assert 7 in ctx["vat_groups"]
        assert ctx["vat_groups"][19]["basis"] == 100.0
        assert ctx["vat_groups"][19]["amount"] == 19.0
        assert ctx["vat_groups"][7]["basis"] == 50.0
        assert ctx["vat_groups"][7]["amount"] == pytest.approx(3.5)
        assert ctx["display_total"] == inv.total_gross

    def test_all_zero_rate_no_vat(self):
        items = [_make_item(price=100, vat_rate=0)]
        inv = _make_invoice(items)
        _resolve_vat(inv, vat_exempt=False, default_vat_rate=0)

        ctx = _prepare_vat_context(inv, vat_exempt=False)

        assert ctx["has_vat"] is False
        assert ctx["display_total"] == inv.total
