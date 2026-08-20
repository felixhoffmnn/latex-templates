import datetime as dt
from xml.etree import ElementTree as ET

import pytest
from factories import make_config, make_customer, make_invoice

from invoice_toolkit.invoice.models.invoices import Invoice, Item
from invoice_toolkit.invoice.template import _resolve_vat
from invoice_toolkit.invoice.xrechnung import generate_xrechnung_xml
from invoice_toolkit.models import Address, Bank, Sender, Tax
from invoice_toolkit.models import Invoice as InvoiceConfig


@pytest.fixture()
def config():
    return make_config(
        sender=Sender(
            address=Address(name="Seller GmbH", street="Seller St 1", zip="12345", city="Berlin", country="DE"),
            email="seller@example.com",
            website="https://seller.example.com",  # type: ignore[invalid-argument-type]
            phone="+49 176 12345678",  # type: ignore[invalid-argument-type]
            tax=Tax(number="12 345 6789 0", office="Berlin", vat_id="DE123456789"),
            bank=Bank(iban="DE89370400440532013000", bic="AAAAAAA1BBB", name="Test Bank"),
        ),
        invoice=InvoiceConfig(VAT=19, due_days=14),
    )


@pytest.fixture()
def customer():
    return make_customer(
        name="Buyer Name",
        email="buyer@example.com",
        phone="+49 176 98765432",
        street="Buyer St 2",
        zip="54321",
        city="Munich",
        buyer_reference="LEITWEG-123",
    )


@pytest.fixture()
def invoice():
    items = [
        Item(name="Service A", quantity=2, unit="Stunde", price=100.0, vat_rate=19),
        Item(name="Product B", quantity=1, unit="Stück", price=50.0, vat_rate=7),
    ]
    inv = make_invoice(
        date=dt.date(2025, 6, 15),
        due_date=dt.date(2025, 6, 29),
        items=items,
    )
    _resolve_vat(inv, vat_exempt=False, default_vat_rate=19)
    return inv


@pytest.fixture()
def xrechnung_root(invoice, customer, config, tmp_path):
    output = tmp_path / "test.xml"
    result = generate_xrechnung_xml(invoice, customer, config, output, vat_exempt=False)
    assert result == output
    assert output.exists()
    tree = ET.parse(output)
    return tree.getroot()


NS = {
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
}


def test_xrechnung_contract(xrechnung_root):
    header_id = xrechnung_root.find(".//rsm:ExchangedDocument/ram:ID", NS)
    seller_name = xrechnung_root.find(".//ram:ApplicableHeaderTradeAgreement/ram:SellerTradeParty/ram:Name", NS)
    buyer_ref = xrechnung_root.find(".//ram:ApplicableHeaderTradeAgreement/ram:BuyerReference", NS)
    line_items = xrechnung_root.findall(".//ram:IncludedSupplyChainTradeLineItem", NS)

    assert header_id is not None and header_id.text == "RE0001"
    assert seller_name is not None and seller_name.text == "Seller GmbH"
    assert buyer_ref is not None and buyer_ref.text == "LEITWEG-123"
    assert len(line_items) == 2


def test_vat_exempt_xrechnung(customer, config, tmp_path):
    invoice = Invoice(
        customer_id=10000,
        invoice_id=1,
        invoice_number="RE0001",
        date=dt.date(2025, 6, 15),
        due_date=dt.date(2025, 6, 29),
        items=[Item(name="Service", quantity=1, unit="Stunde", price=100.0, vat_rate=0)],
    )
    _resolve_vat(invoice, vat_exempt=True, default_vat_rate=0)

    output = generate_xrechnung_xml(invoice, customer, config, tmp_path / "test_exempt.xml", vat_exempt=True)
    assert output.exists()
    assert ET.parse(output).getroot() is not None
