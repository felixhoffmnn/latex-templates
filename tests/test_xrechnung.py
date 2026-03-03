"""Tests for XRechnung XML generation."""

import datetime as dt
from xml.etree import ElementTree as ET

import pytest

from invoice_toolkit.invoice.models.customer import Customer
from invoice_toolkit.invoice.models.invoices import Invoice, Item
from invoice_toolkit.invoice.template import _resolve_vat
from invoice_toolkit.invoice.xrechnung import generate_xrechnung_xml
from invoice_toolkit.models import Address, Bank, Config, Sender, Settings, Tax
from invoice_toolkit.models import Invoice as InvoiceConfig


@pytest.fixture()
def config():
    return Config(
        settings=Settings(open_pdf_viewer=False, open_mail_client=False),
        sender=Sender(
            address=Address(name="Seller GmbH", street="Seller St 1", zip="12345", city="Berlin", country="DE"),
            email="seller@example.com",
            website="https://seller.example.com",
            phone="+49 176 12345678",
            tax=Tax(number="12 345 6789 0", office="Berlin", vat_id="DE123456789"),
            bank=Bank(iban="DE89370400440532013000", bic="AAAAAAA1BBB", name="Test Bank"),
        ),
        invoice=InvoiceConfig(VAT=19, due_days=14),
    )


@pytest.fixture()
def customer():
    return Customer(
        customer_id=10000,
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
    inv = Invoice(
        customer_id=10000,
        invoice_id=1,
        invoice_number="RE0001",
        date=dt.date(2025, 6, 15),
        due_date=dt.date(2025, 6, 29),
        items=items,
    )
    _resolve_vat(inv, vat_exempt=False, default_vat_rate=19)
    return inv


NS = {
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
}


class TestXRechnungGeneration:
    def test_generates_valid_xml(self, invoice, customer, config, tmp_path):
        output = tmp_path / "test.xml"
        result = generate_xrechnung_xml(invoice, customer, config, output, vat_exempt=False)

        assert result == output
        assert output.exists()

        # Should be parseable XML
        tree = ET.parse(output)
        root = tree.getroot()
        assert root is not None

    def test_invoice_number_in_header(self, invoice, customer, config, tmp_path):
        output = tmp_path / "test.xml"
        generate_xrechnung_xml(invoice, customer, config, output, vat_exempt=False)

        tree = ET.parse(output)
        root = tree.getroot()

        header_id = root.find(".//rsm:ExchangedDocument/ram:ID", NS)
        assert header_id is not None
        assert header_id.text == "RE0001"

    def test_seller_name(self, invoice, customer, config, tmp_path):
        output = tmp_path / "test.xml"
        generate_xrechnung_xml(invoice, customer, config, output, vat_exempt=False)

        tree = ET.parse(output)
        root = tree.getroot()

        seller_name = root.find(".//ram:ApplicableHeaderTradeAgreement/ram:SellerTradeParty/ram:Name", NS)
        assert seller_name is not None
        assert seller_name.text == "Seller GmbH"

    def test_buyer_reference(self, invoice, customer, config, tmp_path):
        output = tmp_path / "test.xml"
        generate_xrechnung_xml(invoice, customer, config, output, vat_exempt=False)

        tree = ET.parse(output)
        root = tree.getroot()

        buyer_ref = root.find(".//ram:ApplicableHeaderTradeAgreement/ram:BuyerReference", NS)
        assert buyer_ref is not None
        assert buyer_ref.text == "LEITWEG-123"

    def test_line_items_count(self, invoice, customer, config, tmp_path):
        output = tmp_path / "test.xml"
        generate_xrechnung_xml(invoice, customer, config, output, vat_exempt=False)

        tree = ET.parse(output)
        root = tree.getroot()

        line_items = root.findall(".//ram:IncludedSupplyChainTradeLineItem", NS)
        assert len(line_items) == 2

    def test_vat_exempt_generates_xml(self, customer, config, tmp_path):
        items = [Item(name="Service", quantity=1, unit="Stunde", price=100.0, vat_rate=0)]
        inv = Invoice(
            customer_id=10000,
            invoice_id=1,
            invoice_number="RE0001",
            date=dt.date(2025, 6, 15),
            due_date=dt.date(2025, 6, 29),
            items=items,
        )
        _resolve_vat(inv, vat_exempt=True, default_vat_rate=0)

        output = tmp_path / "test_exempt.xml"
        generate_xrechnung_xml(inv, customer, config, output, vat_exempt=True)

        assert output.exists()
        tree = ET.parse(output)
        assert tree.getroot() is not None
