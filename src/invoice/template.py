import csv
import datetime
import os
import subprocess
from pathlib import Path

import typst
from loguru import logger

from src.invoice import utils
from src.invoice.models.customer import Customer
from src.invoice.models.invoices import Invoice
from src.models import Config
from src.settings import (
    CONFIG_DEFAULT_FILE,
    CONFIG_EXAMPLE_FILE,
    EXAMPLE_DIR,
    INVOICE_CUSTOMER_EXAMPLE_FILE,
    INVOICE_CUSTOMER_FILE,
    INVOICE_DIR,
    INVOICE_EXAMPLE_FILE,
    INVOICE_HISTORY_FILE,
    OUT_DIR,
    TMP_DIR,
)
from src.utils import config_logging, execute_command, is_github_actions, jinja_env, load_config

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

    # Write the invoice data to the file
    with (INVOICE_HISTORY_FILE).open("a") as f:
        csv.writer(f).writerow(
            [
                invoice.invoice_id,
                invoice.customer_id,
                invoice.date.strftime("%Y-%m-%d"),
                invoice.total,
                "sent",
            ]
        )


def archive_pdf(output_file: str, year: int):
    """Archive the pdf file."""
    # Check if the archive directory exists
    (INVOICE_DIR / "archive" / str(year)).mkdir(parents=True, exist_ok=True)

    # Archive the invoice from the output directory to the archive directory
    Path.rename(
        INVOICE_OUT_DIR / (output_file + ".pdf"),
        INVOICE_DIR / "archive" / str(year) / (output_file + ".pdf"),
    )


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
    output_file: Path,
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
    message = f"<p>Hallo {customer.address.name},</p><p>anbei findest du die Rechnung <strong>{invoice.invoice_number}</strong> vom <strong>{invoice.date.strftime('%d.%m.%Y')}</strong>.<br>Bitte überweise den Betrag bis zum <strong>{invoice.due_date.strftime('%d.%m.%Y')}</strong> auf das angegebene Konto (siehe Rechnung).</p><p>Bei Fragen kannst du dich gerne jederzeit melden.</p><p>Viele Grüße<br>{config.sender.address.name}</p>"

    # Create the mail command (opens Thunderbird, containing the mail with the invoice attached)
    email_command = [
        *thunderbird_command,
        "-compose",
        f"from='{config.sender.email}',to='{customer.email}',bcc='{config.sender.email}',subject='{subject}',body='{message}',attachment='{output_file.absolute()}'",
    ]
    logger.debug(f"Email command: {email_command}")

    return email_command


# outsource the code for creating one invoice to a function
def create_invoice(
    invoice: Invoice, config: Config, customer_file: Path, dry_run: bool, verbose: bool, example_mode: bool
):
    """Create one invoice."""
    # Skip invoices that have already been sent or paid
    if invoice.status in ["sent", "paid"]:
        logger.info("Skipping invoice because it has already been sent or paid.")
        return

    # Load customer
    customer = utils.load_customer(customer_file, invoice.customer_id)

    # Create invoice number
    invoice.invoice_id = get_invoice_id(dry_run)
    invoice.invoice_number = f"RE{invoice.invoice_id:04d}"

    # Calculate due date
    if invoice.due_date is None:
        invoice.due_date = invoice.date + datetime.timedelta(days=config.invoice.due_days)

    # Create output and tmp directory if they don't exist
    INVOICE_OUT_DIR.mkdir(parents=True, exist_ok=True)
    INVOICE_TMP_DIR.mkdir(parents=True, exist_ok=True)

    # Load and configure jinja2 template
    template = jinja_env.get_template("invoice.typ.j2")

    # Render the template
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
    )

    # Compose file name for output (contains invoice number, date and customer id)
    output_file = f"{invoice.invoice_number}_{invoice.date.strftime('%Y%m%d')}_{customer.customer_id}"
    generated_typ_file = INVOICE_TMP_DIR / (output_file + ".typ")
    generated_pdf_file = INVOICE_OUT_DIR / (output_file + ".pdf")

    # Store typ file based on invoice number
    with generated_typ_file.open("w") as f:
        f.write(rendered_template)

    # Execute the command to generate the PDF
    typst.compile(str(generated_typ_file), output=str(generated_pdf_file), root="../../")

    # Only run the PDF generation command if not in dry run mode
    if not dry_run and not is_github_actions():
        # If example mode, copy the generated PDF to the example directory
        if example_mode:
            Path.rename(
                generated_pdf_file,
                EXAMPLE_DIR / "invoice.example.pdf",
            )
            generated_pdf_file = EXAMPLE_DIR / "invoice.example.pdf"

        # Open the pdf file
        if config.settings.open_pdf_viewer:
            # Needs to be done before thunderbird is opened, because it will block the terminal
            execute_command(["xdg-open", str(generated_pdf_file)])

        # Generate the email command to open Thunderbird with the invoice attached
        if config.settings.open_mail_client:
            thunderbird_command = get_thunderbird()

            if thunderbird_command:
                execute_command(
                    compose_email(invoice, config, customer, thunderbird_command, generated_pdf_file, dry_run)
                )

        # Ask if everything looked good and if so, archive the invoice and save the invoice number to the csv file
        if not (dry_run or example_mode) and utils.confirm(
            "Did everything look good and do you want to archive the invoice?"
        ):
            # Archive the invoice
            archive_pdf(output_file, invoice.date.year)

            # Save the invoice number
            store_invoice_parameter(invoice)
            logger.success("Invoice archived and invoice number saved.")
        else:
            logger.info("Skipping invoice archiving and invoice number saving.")
    else:
        logger.info("Dry run mode enabled. Skipping PDF generation.")
        logger.debug(f"Rendered template saved to: {generated_typ_file}")
        logger.debug(f"Output file would be saved to: {generated_pdf_file}")


def create_invoices(
    invoices_path: Path | str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
):
    """Create multiple invoices.

    This function will iterate over all invoices in the invoice config file and create them.
    Based on the `customer_id` in the invoice config file, the customer will be loaded from the customer file.
    """
    config_logging(verbose)

    example_mode = invoices_path is None

    if example_mode:
        invoices_path = INVOICE_EXAMPLE_FILE
        customer_database = INVOICE_CUSTOMER_EXAMPLE_FILE
        config_path = CONFIG_EXAMPLE_FILE
    else:
        # Defaults to the data directory if environment variable is not set
        customer_database = INVOICE_CUSTOMER_FILE
        invoices_path = Path(invoices_path)
        # Defaults to project root directory if environment variable is not set
        config_path = Path(os.getenv("CONFIG_PATH", CONFIG_DEFAULT_FILE))

    # Log the used files
    logger.debug(f"Using invoices file: {invoices_path}")
    logger.debug(f"Using customer database: {customer_database}")
    logger.debug(f"Using config file: {config_path}")

    # Check if all files exist
    for file in [Path(invoices_path), customer_database, config_path]:
        if not file.exists():
            raise FileNotFoundError(f"File not found: {file}")

    config = load_config(config_path)

    for invoice in utils.load_invoice(Path(invoices_path)).invoices:
        create_invoice(invoice, config, customer_database, dry_run, verbose, example_mode)
