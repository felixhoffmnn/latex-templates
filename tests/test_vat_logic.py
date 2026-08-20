import pytest
from factories import make_invoice, make_item

from invoice_toolkit.invoice.template import _prepare_vat_context, _resolve_vat


def test_resolve_vat_preserves_explicit_rates_and_computes_totals():
    invoice = make_invoice(
        items=[
            make_item(price=100, vat_rate=None),
            make_item(price=50, vat_rate=7),
            make_item(price=25, vat_rate=0),
        ]
    )
    _resolve_vat(invoice, vat_exempt=False, default_vat_rate=19)

    assert [item.vat_rate for item in invoice.items] == [19, 7, 0]
    assert [item.vat_amount for item in invoice.items] == [19.0, 3.5, 0.0]
    assert (invoice.total, invoice.total_vat, invoice.total_gross) == (175.0, 22.5, 197.5)

    context = _prepare_vat_context(invoice, vat_exempt=False)
    assert context == {
        "has_vat": True,
        "vat_groups": {
            19: {"basis": 100.0, "amount": 19.0},
            7: {"basis": 50.0, "amount": 3.5},
            0: {"basis": 25.0, "amount": 0.0},
        },
        "display_total": 197.5,
    }


@pytest.mark.parametrize("vat_exempt", [True, False])
def test_zero_vat_context(vat_exempt):
    invoice = make_invoice(items=[make_item(price=100, vat_rate=19 if vat_exempt else 0)])
    _resolve_vat(invoice, vat_exempt=vat_exempt, default_vat_rate=0)
    context = _prepare_vat_context(invoice, vat_exempt=vat_exempt)

    assert invoice.items[0].vat_rate == 0
    assert (invoice.total_vat, invoice.total_gross) == (0.0, invoice.total)
    assert context == {"has_vat": False, "vat_groups": {}, "display_total": invoice.total}
