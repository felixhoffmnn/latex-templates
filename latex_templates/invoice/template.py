import datetime
import os
import sqlite3
import subprocess
from email.message import EmailMessage
from pathlib import Path

import jinja2
from loguru import logger

from latex_templates.invoice import utils

DATA_DIR = Path("data")
INVOICE_DIR = DATA_DIR / "invoices"
OUTPUT_DIR = INVOICE_DIR / "out"

TEX_FILE = "invoice.tex"
DB_PATH = INVOICE_DIR / "invoices.db"


def setup_database():
    """Create the database."""
    if not DB_PATH.exists():
        Path.touch(DB_PATH)

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        c.execute(
            """CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                number INTEGER NOT NULL,
                customer TEXT NOT NULL,
                UNIQUE(number)
            )"""
        )


def generate_invoice_number(customer_id: int | str, invoice_id: int | None = None) -> int:
    """Access the database and create a new invoice number.

    Parameters
    ----------
    customer_id : int | str
        The customer id.
    invoice_id : int | None
        The invoice id.

    Returns
    -------
    int
        The new invoice number.
    """
    custom_last_invoice = os.environ.get("LAST_INVOICE", 1)

    # Setup the database
    setup_database()

    # Connect to the database
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        if invoice_id is None:
            # Get the last invoice number
            c.execute("SELECT number FROM invoices ORDER BY id DESC LIMIT 1")
            last_invoice_number = c.fetchone()

            # If there is no last invoice number, use the invoice start
            last_invoice_number = last_invoice_number[0] if last_invoice_number else custom_last_invoice

            # Create the new invoice number
            new_invoice_number = int(last_invoice_number) + 1
        else:
            new_invoice_number = invoice_id

    return new_invoice_number


def save_invoice_id(customer_id: int | str, invoice_id: int):
    """Access the database and store the invoice number.

    This function should only be called after the invoice has been generated, and the user has confirmed that everything looks good.

    Parameters
    ----------
    customer_id : int | str
        The customer id.
    invoice_id : int
        The invoice id.
    """
    # Setup the database
    setup_database()

    # Connect to the database
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        # Insert the new invoice number
        c.execute("INSERT INTO invoices (number, customer) VALUES (?, ?)", (invoice_id, customer_id))


def create_invoice(
    invoice_config: Path | str | None = None,
    customer_config: Path | str | None = None,
    config_config: Path | str | None = None,
    dry_run: bool = False,
):
    """Create invoice."""
    if invoice_config is None:
        invoice_config = INVOICE_DIR / "example.yml"
        customer_config = DATA_DIR / "customers.example.yml"
        config_config = INVOICE_DIR / "config.example.toml"

    invoice_config = Path(invoice_config or INVOICE_DIR / "example.yml")
    customer_config = Path(customer_config or DATA_DIR / "customers.yml")
    config_config = Path(config_config or INVOICE_DIR / "config.toml")

    # Check if all files exist
    for file in [invoice_config, customer_config, config_config]:
        if not file.exists():
            raise FileNotFoundError(f"File not found: {file}")

    config = utils.load_config(config_config)
    invoices = utils.load_invoice(invoice_config)
    customer = utils.load_customer(customer_config, invoices.customer)

    for invoice in invoices.invoices:
        # Skip invoices that have already been sent or paid
        if invoice.status in ["sent", "paid"]:
            logger.info("Skipping invoice because it has already been sent or paid.")
            continue

        # Create invoice number
        invoice.id = generate_invoice_number(customer.id, invoice.id)
        invoice.number = f"RE{invoice.id:04d}"

        # Calculate due date
        if invoice.due_date is None:
            invoice.due_date = invoice.date + datetime.timedelta(days=config.invoice.due_days)

        latex_jinja_env = jinja2.Environment(
            block_start_string="((*",
            block_end_string="*))",
            variable_start_string="(((",
            variable_end_string=")))",
            comment_start_string="((=",
            comment_end_string="=))",
            trim_blocks=True,
            autoescape=False,
            loader=jinja2.FileSystemLoader("templates"),
        )

        template = latex_jinja_env.get_template(TEX_FILE)

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
                    "purpose": f"Rechnung {invoice.number} vom {invoice.date.strftime('%d.%m.%Y')}",
                }
            ),
        )

        # Create output and tmp directory if they don't exist
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        (INVOICE_DIR / "tmp").mkdir(parents=True, exist_ok=True)

        # Store tex file based on invoice number
        with Path.open(INVOICE_DIR / "tmp" / TEX_FILE, "w") as f:
            f.write(rendered_template)

        # Run the generate_pdf command within a Podman container
        latex_command = [
            os.environ.get("CONTAINER_RUNTIME", "podman"),
            "run",
            "--rm",
            "-it",
            "-v",
            f"{Path.cwd()}:/workdir:z",
            "-w",
            "/workdir",
            "--userns",
            f"keep-id:uid={os.getuid()},gid={os.getgid()}",
            "texlive/texlive:latest-full",
            "latexmk",
            f"-output-directory={OUTPUT_DIR}",
            "-pdf",
            "-quiet",
            f"-jobname={invoice.number}",
            str(INVOICE_DIR / "tmp" / TEX_FILE),
        ]

        try:
            subprocess.run(latex_command, check=True)
            logger.success(f"PDF generated successfully at: {OUTPUT_DIR / 'invoice.pdf'}")
        except subprocess.CalledProcessError as e:
            logger.error(f"PDF generation failed: {e}")

        # Check if OPEN_MAIL is set
        if not os.environ.get("OPEN_MAIL", False):
            # Compose the message
            message = f"Hallo {customer.name},\n\nanbei findest du die Rechnung {invoice.number} vom {invoice.date.strftime('%d.%m.%Y')}.\nBitte überweise den Betrag bis zum {invoice.due_date.strftime('%d.%m.%Y')} auf das angegebene Konto (siehe Rechnung).\n\nBei Fragen kannst du dich gerne jederzeit melden.\n\nMit freundlichen Grüßen\n{config.company.name}"

            mail_command = [
                "flatpak",
                "run",
                "org.mozilla.Thunderbird",
                "-compose",
                f"from='{config.company.email}',to='{customer.email}',bcc='{config.company.email}',subject='{"DRY RUN: " if dry_run else ""}Rechnung {invoice.number} vom {invoice.date.strftime('%d.%m.%Y')}',body='{message}',attachment='{(OUTPUT_DIR / invoice.number).absolute()}.pdf'",
            ]

            try:
                subprocess.run(mail_command, check=True)
                logger.success("Mail generated successfully.")
            except subprocess.CalledProcessError as e:
                logger.error(f"Mail generation failed: {e}")
        else:
            logger.info("Skipping mail generation.")

        # Ask if everything looked good and if so, archive the invoice and save the invoice number to the database
        if not dry_run and utils.confirm("Did everything look good?"):
            # Check if the archive directory exists
            (INVOICE_DIR / "archive").mkdir(parents=True, exist_ok=True)

            # Archive the invoice from the output directory to the archive directory
            Path.rename(OUTPUT_DIR / f"{invoice.number}.pdf", INVOICE_DIR / "archive" / f"{invoice.number}.pdf")

            # Save the invoice number
            save_invoice_id(customer.id, invoice.id)
            logger.success("Invoice archived and invoice number saved.")
        else:
            logger.info("Skipping invoice archiving and invoice number saving.")
