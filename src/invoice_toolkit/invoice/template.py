import csv
import datetime
import os
import subprocess
import sys
from pathlib import Path

import typst
from loguru import logger

from invoice_toolkit.invoice import utils
from invoice_toolkit.invoice.models.customer import Customer
from invoice_toolkit.invoice.models.invoices import Invoice
from invoice_toolkit.invoice.xrechnung import generate_xrechnung_xml
from invoice_toolkit.models import Config
from invoice_toolkit.settings import (
    CONFIG_DEFAULT_FILE,
    INVOICE_CUSTOMER_FILE,
    INVOICE_DIR,
    INVOICE_HISTORY_FILE,
    OUT_DIR,
    TMP_DIR,
)
from invoice_toolkit.utils import config_logging, execute_command, jinja_env, load_config, validate_paths

INVOICE_OUT_DIR = OUT_DIR / "invoice"
INVOICE_TMP_DIR = TMP_DIR / "invoice"


def setup_csv_archive(file: Path = INVOICE_HISTORY_FILE):
    """Create the csv archive file if it doesn't exist."""
    if not file.exists():
        with file.open("w") as f:
            csv.writer(f).writerow(["invoice_id", "customer_id", "date", "total", "status"])


def get_invoice_id(
    dry_run: bool,
) -> int:
    """Access the archive csv file and return the next invoice id."""
    custom_last_invoice = int(os.environ.get("LAST_INVOICE", "1"))
    max_invoice_id = 0

    if not dry_run:
        # Setup the csv archive file
        setup_csv_archive()

        # Read the csv file, and get the max invoice id (skip the header)
        with (INVOICE_DIR / "invoice.csv").open("r") as f:
            reader = csv.reader(f)
            next(reader)
            invoice_ids = [int(row[0]) for row in reader if row]

            if invoice_ids:
                # Get the max invoice id
                max_invoice_id = max(invoice_ids)

    # Return the next invoice id
    return int(custom_last_invoice) if max_invoice_id == 0 else max_invoice_id + 1


def store_invoice_parameter(invoice: Invoice):
    """Store the invoice data to a csv file.

    This function should only be called after the invoice has been generated, and the user has confirmed that everything looks good.
    """
    # Create the file if it doesn't exist and add the header (invoice_id,customer_id,date,total,status)
    setup_csv_archive()

    # Use gross total when VAT is applied, otherwise net total
    stored_total = invoice.total_gross if invoice.total_vat > 0 else invoice.total

    # Write the invoice data to the file
    with (INVOICE_HISTORY_FILE).open("a") as f:
        csv.writer(f).writerow(
            [
                invoice.invoice_id,
                invoice.customer_id,
                invoice.date.strftime("%Y-%m-%d"),
                stored_total,
                "sent",
            ]
        )


def archive_invoice(output_file: str, year: int):
    """Archive the invoice PDF and XML files."""
    archive_dir = INVOICE_DIR / "archive" / str(year)
    archive_dir.mkdir(parents=True, exist_ok=True)

    for ext in (".pdf", ".xml"):
        src = INVOICE_OUT_DIR / (output_file + ext)
        if src.exists():
            Path.rename(src, archive_dir / (output_file + ext))


def get_thunderbird():
    """Check if Thunderbird is installed."""
    try:
        # Check if Thunderbird is installed as a snap
        subprocess.run(["thunderbird", "--version"], check=True)
        return ["thunderbird"]
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.info("Thunderbird is not installed bare metal.")

    try:
        # Check if Thunderbird is installed as a flatpak
        subprocess.run(
            ["flatpak", "run", "org.mozilla.Thunderbird", "--version"],
            check=True,
        )
        return ["flatpak", "run", "org.mozilla.Thunderbird"]
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.info("Thunderbird is not installed as a flatpak.")

    logger.warning("Thunderbird is not installed.")
    return None


def compose_email(
    invoice: Invoice,
    config: Config,
    customer: Customer,
    thunderbird_command: list[str],
    pdf_file: Path,
    xml_file: Path,
    dry_run: bool,
):
    """Compose the mail command.

    This function will compose the mail command that will be executed to open Thunderbird with the mail containing the invoice attached.
    """
    # Validate that the due date is set
    if invoice.due_date is None:
        raise ValueError("Due date must be set.")

    subject = (
        f"{'DRY RUN: ' if dry_run else ''}Rechnung {invoice.invoice_number} vom {invoice.date.strftime('%d.%m.%Y')}"
    )
    message = f"<p>Hallo {customer.address.name},</p><p>im Anhang findest du die Rechnung <strong>{invoice.invoice_number}</strong> vom <strong>{invoice.date.strftime('%d.%m.%Y')}</strong>.<br>Bitte überweise den Betrag bis zum <strong>{invoice.due_date.strftime('%d.%m.%Y')}</strong> auf das angegebene Konto (siehe Rechnung).</p><p>Bei Fragen kannst du dich gerne jederzeit melden.</p><p>Viele Grüße<br>{config.sender.address.name}</p>"

    # Attach both PDF and XML
    attachments = str(pdf_file.absolute())
    if xml_file.exists():
        attachments += f",{xml_file.absolute()}"

    # Create the mail command (opens Thunderbird, containing the mail with the invoice attached)
    email_command = [
        *thunderbird_command,
        "-compose",
        f"from='{config.sender.email}',to='{customer.email}',bcc='{config.sender.email}',subject='{subject}',body='{message}',attachment='{attachments}'",
    ]
    logger.debug(f"Email command: {email_command}")

    return email_command


def _resolve_vat(invoice: Invoice, vat_exempt: bool, default_vat_rate: int):
    """Resolve VAT rates for all invoice items.

    When vat_exempt is True (Kleinunternehmer §19 UStG), all items are forced
    to vat_rate=0. When False, items without an explicit vat_rate (None) are
    filled with default_vat_rate; explicit values (including 0) are preserved.
    """
    if vat_exempt:
        for item in invoice.items:
            if item.vat_rate is not None and item.vat_rate > 0:
                logger.warning(f"Item '{item.name}' has vat_rate={item.vat_rate} but vat_exempt is True. Forcing to 0.")
            item.vat_rate = 0
    else:
        for item in invoice.items:
            if item.vat_rate is None:
                item.vat_rate = default_vat_rate

    # Recompute amounts for all items
    for item in invoice.items:
        item.vat_amount = round(item.total * item.vat_rate / 100, 2)
        item.gross_total = item.total + item.vat_amount

    invoice.total_vat = round(sum(i.vat_amount for i in invoice.items), 2)
    invoice.total_gross = round(invoice.total + invoice.total_vat, 2)


def _prepare_vat_context(invoice: Invoice, vat_exempt: bool) -> dict:
    """Build template context for VAT display."""
    has_vat = not vat_exempt and any(i.vat_rate > 0 for i in invoice.items)

    vat_groups: dict[int, dict[str, float]] = {}
    if has_vat:
        for item in invoice.items:
            rate = item.vat_rate
            if rate not in vat_groups:
                vat_groups[rate] = {"basis": 0.0, "amount": 0.0}
            vat_groups[rate]["basis"] = round(vat_groups[rate]["basis"] + item.total, 2)
            vat_groups[rate]["amount"] = round(vat_groups[rate]["amount"] + item.vat_amount, 2)

    return {
        "has_vat": has_vat,
        "vat_groups": vat_groups,
        "display_total": invoice.total_gross if has_vat else invoice.total,
    }


def _handle_post_generation(
    invoice: Invoice,
    config: Config,
    customer: Customer,
    output_file: str,
    generated_pdf_file: Path,
    generated_xml_file: Path,
    dry_run: bool,
):
    """Handle post-generation steps: PDF viewing, email, archiving."""
    if config.settings.open_pdf_viewer:
        execute_command(["xdg-open", str(generated_pdf_file)])

    if config.settings.open_mail_client:
        thunderbird_command = get_thunderbird()
        if thunderbird_command:
            execute_command(
                compose_email(
                    invoice,
                    config,
                    customer,
                    thunderbird_command,
                    generated_pdf_file,
                    generated_xml_file,
                    dry_run,
                )
            )

    if not dry_run and utils.confirm("Did everything look good and do you want to archive the invoice?"):
        archive_invoice(output_file, invoice.date.year)
        store_invoice_parameter(invoice)
        logger.success("Invoice archived and invoice number saved.")
    else:
        logger.info("Skipping invoice archiving and invoice number saving.")


def create_invoice(
    invoice: Invoice,
    config: Config,
    customer_file: Path,
    dry_run: bool,
    verbose: bool,
    output: Path | None = None,
):
    """Create one invoice."""
    if invoice.status in ["sent", "paid"]:
        logger.info("Skipping invoice because it has already been sent or paid.")
        return

    customer = utils.load_customer(customer_file, invoice.customer_id)

    invoice.invoice_id = get_invoice_id(dry_run)
    invoice.invoice_number = f"RE{invoice.invoice_id:04d}"

    if invoice.due_date is None:
        invoice.due_date = invoice.date + datetime.timedelta(days=config.invoice.due_days)

    INVOICE_OUT_DIR.mkdir(parents=True, exist_ok=True)
    INVOICE_TMP_DIR.mkdir(parents=True, exist_ok=True)

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
    generated_typ_file = INVOICE_TMP_DIR / (output_file + ".typ")
    generated_pdf_file = INVOICE_OUT_DIR / (output_file + ".pdf")
    generated_xml_file = INVOICE_OUT_DIR / (output_file + ".xml")

    with generated_typ_file.open("w") as f:
        f.write(rendered_template)

    typst.compile(str(generated_typ_file), output=str(generated_pdf_file), root="../../")
    generate_xrechnung_xml(invoice, customer, config, generated_xml_file, config.invoice.vat_exempt)

    if output is not None:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        generated_pdf_file.rename(Path(f"{output}.pdf"))
        if generated_xml_file.exists():
            generated_xml_file.rename(Path(f"{output}.xml"))
        return

    if not dry_run:
        _handle_post_generation(
            invoice,
            config,
            customer,
            output_file,
            generated_pdf_file,
            generated_xml_file,
            dry_run,
        )
    else:
        logger.info("Dry run mode enabled. Skipping PDF generation.")
        logger.debug(f"Rendered template saved to: {generated_typ_file}")
        logger.debug(f"Output file would be saved to: {generated_pdf_file}")
        logger.debug(f"XRechnung XML saved to: {generated_xml_file}")


def create_invoices(
    invoices_path: Path | str | None = None,
    config_path: Path | str | None = None,
    customer_path: Path | str | None = None,
    output: Path | str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
    make_all: bool = False,
):
    """Create multiple invoices.

    This function will iterate over all invoices in the invoice config file and create them.
    Based on the `customer_id` in the invoice config file, the customer will be loaded from the customer file.
    """
    config_logging(verbose)

    if invoices_path is None:
        logger.error("Missing required argument: invoices_path")
        sys.exit(1)

    invoices_path = Path(invoices_path)
    customer_database = Path(customer_path) if customer_path else INVOICE_CUSTOMER_FILE
    config_path = Path(config_path) if config_path else Path(os.getenv("CONFIG_PATH", CONFIG_DEFAULT_FILE))

    # Log the used files
    logger.debug(f"Using invoices file: {invoices_path}")
    logger.debug(f"Using customer database: {customer_database}")
    logger.debug(f"Using config file: {config_path}")

    # Check if all required paths exist
    paths_to_validate = [
        (invoices_path, "invoices file"),
        (customer_database, "customer database"),
        (config_path, "config file"),
    ]
    if not dry_run:
        paths_to_validate.insert(0, (INVOICE_DIR, "invoice data directory"))

    validate_paths(paths_to_validate)

    config = load_config(config_path)

    all_invoices = utils.load_invoice(invoices_path).invoices

    if dry_run or make_all:
        invoices_to_process = all_invoices
    else:
        invoices_to_process = utils.select_invoice(all_invoices, customer_database)
        if not invoices_to_process:
            logger.info("No draft invoices found.")
            return

    for invoice in invoices_to_process:
        create_invoice(
            invoice,
            config,
            customer_database,
            dry_run,
            verbose,
            output=Path(output) if output else None,
        )
