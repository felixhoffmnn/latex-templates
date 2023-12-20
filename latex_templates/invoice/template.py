import csv
import datetime
import os
import subprocess
from pathlib import Path

from loguru import logger

from latex_templates.invoice import utils
from latex_templates.invoice.models.customer import Customer
from latex_templates.invoice.models.invoice import Invoice
from latex_templates.models import Config
from latex_templates.utils import compose_latex_command, latex_jinja_env, load_config

DATA_DIR = Path("data")
INVOICE_DIR = Path(os.getenv("INVOICE_PATH", DATA_DIR))
EXAMPLE_DIR = Path("example")
OUTPUT_DIR = Path("out/invoices")
TMP_DIR = Path("tmp/invoices")


def setup_csv_archive(file: Path = INVOICE_DIR / "invoice.csv"):
    """Create the csv archive file if it doesn't exist."""
    if not file.exists():
        with file.open("w") as f:
            csv.writer(f).writerow(["invoice_id", "customer_id", "date", "total", "status"])


def get_invoice_id(invoice: Invoice) -> int:
    """Access the archive csv file and return the next invoice id."""
    custom_last_invoice = os.environ.get("LAST_INVOICE", 1)

    # Setup the csv archive file
    setup_csv_archive()

    # Read the csv file, and get the max invoice id (skip the header)
    with (INVOICE_DIR / "invoice.csv").open("r") as f:
        reader = csv.reader(f)
        next(reader)
        invoice_ids = [int(row[0]) for row in reader if row]

    # Get the max invoice id
    max_invoice_id = max(invoice_ids) if invoice_ids else 0

    # Return the next invoice id
    return int(custom_last_invoice) if max_invoice_id == 0 else max_invoice_id + 1


def store_invoice_parameter(invoice: Invoice):
    """Store the invoice data to a csv file.

    This function should only be called after the invoice has been generated, and the user has confirmed that everything looks good.
    """
    # Create the file if it doesn't exist and add the header (invoice_id,customer_id,date,total,status)
    setup_csv_archive()

    # Write the invoice data to the file
    with (INVOICE_DIR / "invoice.csv").open("a") as f:
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
    (INVOICE_DIR / "archive").mkdir(parents=True, exist_ok=True)

    # Archive the invoice from the output directory to the archive directory
    Path.rename(
        OUTPUT_DIR / (output_file + ".pdf"),
        INVOICE_DIR / "archive" / str(year) / (output_file + ".pdf"),
    )


def compose_email(
    invoice: Invoice,
    config: Config,
    customer: Customer,
    output_file: str,
    dry_run: bool,
):
    """Compose the mail command.

    This function will compose the mail command that will be executed to open Thunderbird with the mail containing the invoice attached.
    """
    # Validate that the due date is set
    if invoice.due_date is None:
        raise ValueError("Due date must be set.")

    subject = (
        f"{"DRY RUN: " if dry_run else ""}Rechnung {invoice.invoice_number} vom {invoice.date.strftime('%d.%m.%Y')}"
    )
    message = f"Hallo {customer.name},\n\nanbei findest du die Rechnung {invoice.invoice_number} vom {invoice.date.strftime('%d.%m.%Y')}.\nBitte überweise den Betrag bis zum {invoice.due_date.strftime('%d.%m.%Y')} auf das angegebene Konto (siehe Rechnung).\n\nBei Fragen kannst du dich gerne jederzeit melden.\n\nMit freundlichen Grüßen\n{config.company.name}"

    # Create the mail command (opens Thunderbird, containing the mail with the invoice attached)
    email_command = [
        "flatpak",
        "run",
        "org.mozilla.Thunderbird",
        "-compose",
        f"from='{config.company.email}',to='{customer.email}',bcc='{config.company.email}',subject='{subject}',body='{message}',attachment='{(OUTPUT_DIR / output_file).absolute()}.pdf'",
    ]

    return email_command


# outsource the code for creating one invoice to a function
def create_invoice(invoice: Invoice, config: Config, customer_file: Path, dry_run: bool, latex_quiet: bool = True):
    """Create one invoice."""
    # Skip invoices that have already been sent or paid
    if invoice.status in ["sent", "paid"]:
        logger.info("Skipping invoice because it has already been sent or paid.")
        return

    # Load customer
    customer = utils.load_customer(customer_file, invoice.customer_id)

    # Create invoice number
    invoice.invoice_id = get_invoice_id(invoice)
    invoice.invoice_number = f"RE{invoice.invoice_id:04d}"

    # Calculate due date
    if invoice.due_date is None:
        invoice.due_date = invoice.date + datetime.timedelta(days=config.invoice.due_days)

    # Load and configure jinja2 template
    template = latex_jinja_env.get_template("invoice.tex.j2")

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

    # Create output and tmp directory if they don't exist
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    # Compose file name for output (contains invoice number, date and customer id)
    output_file = f"{invoice.invoice_number}_{invoice.date.strftime('%Y%m%d')}_{customer.customer_id}"

    # Store tex file based on invoice number
    with (TMP_DIR / (output_file + ".tex")).open("w") as f:
        f.write(rendered_template)

    # Run the generate_pdf command within a Podman container
    latex_command = compose_latex_command(OUTPUT_DIR, TMP_DIR / (output_file + ".tex"), latex_quiet)

    logger.debug(f"Running command: {latex_command}")

    try:
        subprocess.run(latex_command, check=True)
        logger.success(f"PDF generated successfully at: {OUTPUT_DIR / (output_file + '.pdf')}")
    except subprocess.CalledProcessError as e:
        logger.error(f"PDF generation failed: {e}")

    # Check if OPEN_MAIL is set
    if not os.environ.get("OPEN_MAIL", False):
        # Create the subject and message for the mail
        email_command = compose_email(invoice, config, customer, output_file, dry_run)

        try:
            subprocess.run(email_command, check=True)
            logger.success("Mail generated successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Mail generation failed: {e}")
    else:
        logger.info("Skipping mail generation.")

    # Ask if everything looked good and if so, archive the invoice and save the invoice number to the csv file
    if not dry_run and utils.confirm("Did everything look good?") and INVOICE_DIR is not None:
        # Archive the invoice
        archive_pdf(output_file, invoice.date.year)

        # Save the invoice number
        store_invoice_parameter(invoice)
        logger.success("Invoice archived and invoice number saved.")
    else:
        logger.info("Skipping invoice archiving and invoice number saving.")


def create_invoices(
    invoice_config: Path | str | None = None,
    customer_file: Path | str | None = None,
    base_config: Path | str | None = None,
    dry_run: bool = False,
):
    """Create multiple invoices.

    This function will iterate over all invoices in the invoice config file and create them.
    Based on the `customer_id` in the invoice config file, the customer will be loaded from the customer file.
    """
    if (invoice_config or customer_file or base_config) is None:
        invoice_config = EXAMPLE_DIR / "invoices.example.yml"
        customer_file = EXAMPLE_DIR / "customer.example.csv"
        base_config = EXAMPLE_DIR / "config.example.toml"

        logger.warning("No config files specified. Using example config files.")

    invoice_config = Path(invoice_config or DATA_DIR / "invoices.yml")
    customer_file = Path(customer_file or INVOICE_DIR / "customer.csv")
    base_config = Path(base_config or Path("config.toml"))

    # Check if all files exist
    for file in [invoice_config, customer_file, base_config]:
        if not file.exists():
            raise FileNotFoundError(f"File not found: {file}")

    config = load_config(base_config)
    invoices = utils.load_invoice(invoice_config)

    for invoice in invoices:
        create_invoice(invoice, config, customer_file, dry_run)
