"""Invoice generation workflow including rendering, PDF compilation, and archiving."""

from __future__ import annotations

import csv
import datetime
import logging
import os
import shutil
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

import typst

from invoice_toolkit.invoice import utils
from invoice_toolkit.invoice.xrechnung import generate_xrechnung_xml

if TYPE_CHECKING:
    from pathlib import Path

    import jinja2

    from invoice_toolkit.invoice.models.customer import Customer
    from invoice_toolkit.invoice.models.invoices import Invoice
    from invoice_toolkit.models import Config
    from invoice_toolkit.settings import ProjectPaths

logger = logging.getLogger(__name__)

# Counter used to generate unique IDs in dry-run mode across a batch
_dry_run_counter = 0


@dataclass(frozen=True)
class InvoiceResult:
    """Result of a single invoice generation."""

    pdf_path: Path
    xml_path: Path
    invoice: Invoice
    customer: Customer
    config: Config
    output_file: str


def setup_csv_archive(file: Path):
    """Create the csv archive file if it doesn't exist.

    Raises OSError if the file cannot be created.
    """
    if not file.exists():
        try:
            with file.open("w") as f:
                csv.writer(f).writerow(["invoice_id", "customer_id", "date", "total", "status"])
        except OSError as e:
            raise OSError(f"Failed to create CSV archive {file}: {e}") from e


def get_invoice_id(dry_run: bool, history_file: Path) -> int:
    """Access the archive csv file and return the next invoice id."""
    global _dry_run_counter  # noqa: PLW0603

    custom_last_invoice = int(os.environ.get("LAST_INVOICE", "1"))

    if dry_run:
        _dry_run_counter += 1
        return custom_last_invoice + _dry_run_counter - 1

    setup_csv_archive(history_file)

    try:
        with history_file.open("r") as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header, safe if file is empty
            invoice_ids = []
            for row in reader:
                if row:
                    try:
                        invoice_ids.append(int(row[0]))
                    except ValueError, IndexError:
                        logger.warning(f"Skipping malformed row in {history_file}: {row}")
    except FileNotFoundError:
        logger.warning(f"Invoice history file not found: {history_file}")
        return custom_last_invoice

    if not invoice_ids:
        return custom_last_invoice

    return max(invoice_ids) + 1


def store_invoice_parameter(invoice: Invoice, history_file: Path):
    """Store the invoice data to a csv file.

    This function should only be called after the invoice has been generated, and the user has confirmed that everything looks good.
    """
    setup_csv_archive(history_file)

    # Use gross total when VAT is applied, otherwise net total
    stored_total = invoice.total_gross if invoice.total_vat and invoice.total_vat > 0 else invoice.total

    try:
        with history_file.open("a") as f:
            csv.writer(f).writerow(
                [
                    invoice.invoice_id,
                    invoice.customer_id,
                    invoice.date.strftime("%Y-%m-%d"),
                    stored_total,
                    "sent",
                ]
            )
    except OSError as e:
        raise OSError(f"Failed to write invoice parameters to {history_file}: {e}") from e


def archive_invoice(output_file: str, year: int, out_dir: Path, data_dir: Path):
    """Archive the invoice PDF and XML files."""
    invoice_out_dir = out_dir / "invoice"
    archive_dir = data_dir / "archive" / str(year)
    archive_dir.mkdir(parents=True, exist_ok=True)

    for ext in (".pdf", ".xml"):
        src = invoice_out_dir / (output_file + ext)
        if src.exists():
            try:
                shutil.move(str(src), str(archive_dir / (output_file + ext)))
            except OSError as e:
                raise OSError(f"Failed to archive {src} to {archive_dir}: {e}") from e
        else:
            logger.debug(f"Skipping archive of missing file: {src}")


def _resolve_vat(invoice: Invoice, vat_exempt: bool, default_vat_rate: Literal[0, 7, 19]):
    """Resolve VAT rates for all invoice items.

    When vat_exempt is True (Kleinunternehmer §19 UStG), all items are forced
    to vat_rate=0. When False, items without an explicit vat_rate (None) are
    filled with default_vat_rate; explicit values (including 0) are preserved.
    """
    for item in invoice.items:
        if vat_exempt:
            if item.vat_rate is not None and item.vat_rate > 0:
                logger.warning(f"Item '{item.name}' has vat_rate={item.vat_rate} but vat_exempt is True. Forcing to 0.")
            item.vat_rate = 0
        elif item.vat_rate is None:
            item.vat_rate = default_vat_rate

        if item.vat_rate is None:
            raise ValueError(f"Item '{item.name}' has no VAT rate after resolution")
        item.vat_amount = round(item.total * item.vat_rate / 100, 2)
        item.gross_total = item.total + item.vat_amount

    invoice.total_vat = round(sum(i.vat_amount for i in invoice.items), 2)
    invoice.total_gross = round(invoice.total + invoice.total_vat, 2)


def _prepare_vat_context(invoice: Invoice, vat_exempt: bool) -> dict:
    """Build template context for VAT display."""
    has_vat = not vat_exempt and any(i.vat_rate is not None and i.vat_rate > 0 for i in invoice.items)

    vat_groups: dict[int, dict[str, float]] = {}
    if has_vat:
        for item in invoice.items:
            rate = item.vat_rate
            if rate is None:
                raise ValueError(f"Item '{item.name}' has no VAT rate in VAT context preparation")
            if rate not in vat_groups:
                vat_groups[rate] = {"basis": 0.0, "amount": 0.0}
            vat_groups[rate]["basis"] = round(vat_groups[rate]["basis"] + item.total, 2)
            vat_groups[rate]["amount"] = round(vat_groups[rate]["amount"] + item.vat_amount, 2)

    return {
        "has_vat": has_vat,
        "vat_groups": vat_groups,
        "display_total": invoice.total_gross if has_vat else invoice.total,
    }


def create_invoice(
    invoice: Invoice,
    config: Config,
    customer_file: Path,
    dry_run: bool,
    paths: ProjectPaths,
    jinja_env: jinja2.Environment,
    output: Path | None = None,
) -> InvoiceResult | None:
    """Create one invoice and return the result.

    Returns None if the invoice is skipped (already sent/paid).
    """
    if invoice.status in ["sent", "paid"]:
        logger.info("Skipping invoice because it has already been sent or paid.")
        return None

    invoice_out_dir = paths.out_dir / "invoice"
    invoice_tmp_dir = paths.tmp_dir / "invoice"

    customer = utils.load_customer(customer_file, invoice.customer_id)

    invoice.invoice_id = get_invoice_id(dry_run, paths.invoice_history_file)
    invoice.invoice_number = f"RE{invoice.invoice_id:04d}"

    if invoice.due_date is None:
        invoice.due_date = invoice.date + datetime.timedelta(days=config.invoice.due_days)

    invoice_out_dir.mkdir(parents=True, exist_ok=True)
    invoice_tmp_dir.mkdir(parents=True, exist_ok=True)

    _resolve_vat(invoice, config.invoice.vat_exempt, config.invoice.default_vat_rate)
    vat_context = _prepare_vat_context(invoice, config.invoice.vat_exempt)

    template = jinja_env.get_template("invoice.typ.j2")
    rendered_template = template.render(
        config=config,
        customer=customer,
        invoice=invoice.model_copy(
            update={
                "date": invoice.date.strftime("%d.%m.%Y"),
                "start_date": invoice.start_date.strftime("%d.%m.%Y") if invoice.start_date else None,
                "end_date": invoice.end_date.strftime("%d.%m.%Y") if invoice.end_date else None,
                "due_date": invoice.due_date.strftime("%d.%m.%Y"),
            }
        ),
        additional={"purpose": f"Rechnung {invoice.invoice_number} vom {invoice.date.strftime('%d.%m.%Y')}"},
        **vat_context,
    )

    output_file = f"{invoice.invoice_number}_{invoice.date.strftime('%Y%m%d')}_{customer.customer_id}"
    generated_typ_file = invoice_tmp_dir / (output_file + ".typ")
    generated_pdf_file = invoice_out_dir / (output_file + ".pdf")
    generated_xml_file = invoice_out_dir / (output_file + ".xml")

    try:
        with generated_typ_file.open("w") as f:
            f.write(rendered_template)
    except OSError as e:
        raise OSError(f"Failed to write Typst file {generated_typ_file}: {e}") from e

    try:
        typst.compile(str(generated_typ_file), output=str(generated_pdf_file), root=str(paths.project_root))
    except Exception as e:
        raise RuntimeError(f"Typst compilation failed for {generated_typ_file}: {e}") from e

    generate_xrechnung_xml(invoice, customer, config, generated_xml_file, config.invoice.vat_exempt)

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        final_pdf = output.with_suffix(".pdf")
        final_xml = output.with_suffix(".xml")
        shutil.move(str(generated_pdf_file), str(final_pdf))
        if generated_xml_file.exists():
            shutil.move(str(generated_xml_file), str(final_xml))
        return InvoiceResult(
            pdf_path=final_pdf,
            xml_path=final_xml,
            invoice=invoice,
            customer=customer,
            config=config,
            output_file=output_file,
        )

    return InvoiceResult(
        pdf_path=generated_pdf_file,
        xml_path=generated_xml_file,
        invoice=invoice,
        customer=customer,
        config=config,
        output_file=output_file,
    )


def create_invoices(
    invoices: list[Invoice],
    config: Config,
    customer_file: Path,
    dry_run: bool,
    paths: ProjectPaths,
    jinja_env: jinja2.Environment,
    output: Path | None = None,
) -> list[InvoiceResult]:
    """Create multiple invoices from a pre-selected list.

    Returns a list of InvoiceResult for each successfully generated invoice.
    """
    global _dry_run_counter  # noqa: PLW0603
    _dry_run_counter = 0

    results: list[InvoiceResult] = []

    for invoice in invoices:
        result = create_invoice(
            invoice,
            config,
            customer_file,
            dry_run,
            paths,
            jinja_env,
            output=output,
        )
        if result is not None:
            results.append(result)

    return results
