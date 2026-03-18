"""XRechnung CII XML generation using the drafthorse library."""

import logging
from decimal import Decimal
from typing import TYPE_CHECKING

from invoice_toolkit.invoice.utils import group_items_by_vat

if TYPE_CHECKING:
    from pathlib import Path

    from drafthorse.models.document import Document

    from invoice_toolkit.invoice.models.customer import Customer
    from invoice_toolkit.invoice.models.invoices import Invoice, Item
    from invoice_toolkit.models import Config, Sender

logger = logging.getLogger(__name__)

UNIT_CODE_MAP = {
    "Stunde": "HUR",
    "Stück": "H87",
    "Monat": "MON",
}


def _set_seller(doc: Document, sender: Sender):
    """Set seller (BG-4) trade party on the document."""
    from drafthorse.models.party import TaxRegistration

    seller = doc.trade.agreement.seller
    seller.name = sender.address.name
    seller.address.line_one = sender.address.street
    seller.address.postcode = str(sender.address.zip)
    seller.address.city_name = sender.address.city
    seller.address.country_id = sender.address.country or "DE"
    seller.electronic_address.uri_ID = ("EM", str(sender.email))
    seller.contact.person_name = sender.address.name
    seller.contact.telephone.number = str(sender.phone).replace("tel:", "").replace("-", "")
    seller.contact.email.address = str(sender.email)
    seller.tax_registrations.add(TaxRegistration(id=("FC", sender.tax.number)))
    if sender.tax.vat_id:
        seller.tax_registrations.add(TaxRegistration(id=("VA", sender.tax.vat_id)))
    seller.legal_organization.id = sender.tax.number


def _set_buyer(doc: Document, customer: Customer):
    """Set buyer (BG-7) trade party on the document."""
    buyer = doc.trade.agreement.buyer
    buyer.name = customer.company or customer.address.name
    buyer.address.line_one = customer.address.street
    buyer.address.postcode = str(customer.address.zip)
    buyer.address.city_name = customer.address.city
    buyer.address.country_id = customer.address.country or "DE"
    buyer.electronic_address.uri_ID = ("EM", str(customer.email))


def _add_line_item(doc: Document, idx: int, item: Item, vat_exempt: bool):
    """Add a single line item to the document."""
    from drafthorse.models.tradelines import LineItem

    li = LineItem()
    li.document.line_id = str(idx)
    li.product.name = item.name
    if item.description:
        li.product.description = item.description

    unit_code = UNIT_CODE_MAP.get(item.unit, "C62")
    li.agreement.net.amount = Decimal(str(item.price))
    li.agreement.net.basis_quantity = (Decimal("1"), unit_code)
    li.delivery.billed_quantity = (Decimal(str(item.quantity)), unit_code)

    li.settlement.trade_tax.type_code = "VAT"
    if item.vat_rate is None:
        raise ValueError(f"Line item '{item.name}' has no VAT rate")
    if item.vat_rate > 0:
        li.settlement.trade_tax.category_code = "S"
        li.settlement.trade_tax.rate_applicable_percent = Decimal(str(item.vat_rate))
    elif vat_exempt:
        li.settlement.trade_tax.category_code = "E"
        li.settlement.trade_tax.rate_applicable_percent = Decimal("0")
    else:
        li.settlement.trade_tax.category_code = "Z"
        li.settlement.trade_tax.rate_applicable_percent = Decimal("0")

    li.settlement.monetary_summation.total_amount = Decimal(str(item.total))
    doc.trade.items.add(li)


def _set_settlement(doc: Document, invoice: Invoice, sender: Sender, vat_exempt: bool):
    """Set settlement: payment means, terms, tax summaries, and monetary summation."""
    from drafthorse.models.payment import PaymentMeans, PaymentTerms

    doc.trade.settlement.currency_code = "EUR"
    doc.trade.settlement.payment_reference = (
        f"Rechnung {invoice.invoice_number} vom {invoice.date.strftime('%d.%m.%Y')}"
    )

    # Payment means: SEPA credit transfer
    pm = PaymentMeans()
    pm.type_code = "58"
    pm.payee_account.iban = sender.bank.iban.replace(" ", "")
    pm.payee_account.account_name = sender.address.name
    pm.payee_institution.bic = sender.bank.bic
    doc.trade.settlement.payment_means.add(pm)

    # Payment terms
    if invoice.due_date:
        terms = PaymentTerms()
        terms.description = f"Zahlbar bis zum {invoice.due_date.strftime('%d.%m.%Y')}"
        terms.due = invoice.due_date
        doc.trade.settlement.terms.add(terms)

    # Document-level tax summaries (BG-23)
    _add_tax_summaries(doc, invoice, vat_exempt)

    # Monetary summation (BG-22)
    _set_monetary_summation(doc, invoice)


def _add_tax_summaries(doc: Document, invoice: Invoice, vat_exempt: bool):
    """Add document-level tax summaries grouped by VAT rate."""
    from drafthorse.models.accounting import ApplicableTradeTax

    for rate, group in sorted(group_items_by_vat(invoice.items).items()):
        tax = ApplicableTradeTax()
        tax.calculated_amount = Decimal(str(group.amount))
        tax.type_code = "VAT"
        tax.basis_amount = Decimal(str(group.basis))

        if rate > 0:
            tax.category_code = "S"
            tax.rate_applicable_percent = Decimal(str(rate))
        elif vat_exempt:
            tax.category_code = "E"
            tax.rate_applicable_percent = Decimal("0")
            tax.exemption_reason = "Kein Ausweis von Umsatzsteuer, da Kleinunternehmer gemäß §19 UStG."
            tax.exemption_reason_code = "vatex-eu-o"
        else:
            tax.category_code = "Z"
            tax.rate_applicable_percent = Decimal("0")

        doc.trade.settlement.trade_tax.add(tax)


def _set_monetary_summation(doc: Document, invoice: Invoice):
    """Set the monetary summation totals (BG-22)."""
    net_total = Decimal(str(invoice.total))
    vat_total = Decimal(str(invoice.total_vat))
    gross_total = Decimal(str(invoice.total_gross))

    ms = doc.trade.settlement.monetary_summation
    ms.line_total = net_total
    ms.charge_total = Decimal("0.00")
    ms.allowance_total = Decimal("0.00")
    ms.tax_basis_total = net_total
    ms.tax_total = (vat_total, "EUR")
    ms.grand_total = gross_total
    ms.prepaid_total = Decimal("0.00")
    ms.due_amount = gross_total


def generate_xrechnung_xml(
    invoice: Invoice, customer: Customer, config: Config, output_path: Path, vat_exempt: bool = False
) -> Path:
    """Generate an XRechnung CII XML file for the given invoice.

    Parameters
    ----------
    invoice : Invoice
        The invoice with computed totals and assigned invoice_number.
    customer : Customer
        The customer/buyer for this invoice.
    config : Config
        Application config with sender, bank, and tax details.
    output_path : Path
        The output XML file path.
    vat_exempt : bool
        Whether the sender is VAT-exempt (Kleinunternehmer §19 UStG).

    Returns:
    -------
    Path
        The path to the generated XML file.
    """
    try:
        from drafthorse.models.document import Document
    except ImportError as e:
        raise ImportError(
            "The 'drafthorse' package is required for XRechnung XML generation. "
            "Install it with: pip install invoice-toolkit[xrechnung]"
        ) from e

    doc = Document()

    # Context: XRechnung 3.0 CII profile
    doc.context.business_parameter.id = "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"
    doc.context.guideline_parameter.id = "urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0"

    # Header
    doc.header.id = invoice.invoice_number
    doc.header.type_code = "380"
    doc.header.issue_date_time = invoice.date

    # Buyer reference (BT-10): invoice-level priority, customer-level fallback
    buyer_ref = invoice.buyer_reference or customer.buyer_reference or "n/a"
    doc.trade.agreement.buyer_reference = buyer_ref

    # Trade parties
    _set_seller(doc, config.sender)
    _set_buyer(doc, customer)

    # Delivery
    doc.trade.delivery.event.occurrence = invoice.end_date or invoice.date

    # Line items
    for idx, item in enumerate(invoice.items, start=1):
        _add_line_item(doc, idx, item, vat_exempt)

    _set_settlement(doc, invoice, config.sender, vat_exempt)

    # Serialize
    try:
        xml_bytes = doc.serialize(schema=None)
    except Exception as e:
        raise RuntimeError(f"Failed to serialize XRechnung XML: {e}") from e

    try:
        output_path.write_bytes(xml_bytes)
    except OSError as e:
        raise OSError(f"Failed to write XRechnung XML to {output_path}: {e}") from e

    logger.info(f"XRechnung XML generated: {output_path}")

    return output_path
