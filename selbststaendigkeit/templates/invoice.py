import datetime
import os
import sqlite3
import subprocess
from pathlib import Path

import jinja2
from loguru import logger

from selbststaendigkeit.utils import models

CUSTOMER_FILE = Path(os.environ.get("CUSTOMER_FILE", "data/customers.example.yml"))
CONFIG_FILE = Path(os.environ.get("CONFIG_FILE", "config.example.toml"))


def create_invoice_number() -> int:
    """Access the database and create a new invoice number.

    The invoice number format is: REXXXX.
    """
    # Create a sqlite database if it doesn't exist
    db_path = Path("invoices/invoices.db")
    if not db_path.exists():
        with db_path.open("w") as f:
            pass

    # Connect to the database
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Create table if it doesn't exist
    c.execute(
        """CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT NOT NULL,
            UNIQUE(number)
        )"""
    )

    # Get the last invoice number
    c.execute("SELECT number FROM invoices ORDER BY id DESC LIMIT 1")
    last_invoice_number = c.fetchone()

    # Create a new invoice number
    new_invoice_number = "RE0001" if last_invoice_number is None else f"RE{int(last_invoice_number[0][2:]) + 1:04d}"

    # Insert the new invoice number into the database
    c.execute("INSERT INTO invoices (number) VALUES (?)", (new_invoice_number,))
    conn.commit()
    conn.close()

    # Return the new invoice number
    return new_invoice_number


def create_invoice(invoice_path: Path = Path("invoices/example.yml")):
    """Create invoice."""
    config = models.load_config(CONFIG_FILE)
    invoice = models.load_invoice(invoice_path)
    customer = models.load_customer(CUSTOMER_FILE, invoice.customer)

    # Create invoice number
    config.invoice.number = create_invoice_number()

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

    template = latex_jinja_env.get_template("invoice.tex")

    # Render the template
    rendered_template = template.render(
        config=config,
        customer=customer,
        invoice=invoice.model_copy(
            update={
                "date": invoice.date.strftime("%d.%m.%Y"),
                "due_date": (invoice.date + datetime.timedelta(days=config.invoice.due_days)).strftime("%d.%m.%Y"),
            }
        ),
    )

    # Store tex file based on invoice number
    with Path.open("invoices/tmp/invoice.tex", "w") as f:
        f.write(rendered_template)

    output_directory = Path("invoices/out")

    # Run the generate_pdf command within a Podman container
    podman_command = [
        "podman",
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
        f"-output-directory={output_directory}",
        "-pdf",
        "-quiet",
        "invoices/tmp/invoice.tex",
    ]

    try:
        subprocess.run(podman_command, check=True)
        logger.success(f"PDF generated successfully at: {output_directory}")
    except subprocess.CalledProcessError as e:
        logger.error(f"PDF generation failed: {e}")
