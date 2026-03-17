"""Invoice subcommands and post-generation orchestration."""

from __future__ import annotations

import csv
import logging
import subprocess
import sys
from pathlib import Path  # noqa: TC003 - needed at runtime by Typer
from typing import TYPE_CHECKING, Annotated

import typer

if TYPE_CHECKING:
    from invoice_toolkit.invoice.models.invoices import Invoice
    from invoice_toolkit.settings import ProjectPaths

from invoice_cli.utils import (
    compose_email,
    confirm,
    default_project_paths,
    execute_command,
    get_thunderbird,
    resolve_config_path,
    resolve_invoices_path,
    validate_paths,
)
from invoice_toolkit.invoice import utils
from invoice_toolkit.invoice.models import Invoices
from invoice_toolkit.invoice.template import (
    InvoiceResult,
    archive_invoice,
    create_invoices,
    store_invoice_parameter,
)
from invoice_toolkit.models import Config
from invoice_toolkit.utils import create_jinja_env, load_yaml_model

logger = logging.getLogger(__name__)


def _parse_selection(raw: str, max_index: int) -> list[int] | None:
    """Parse a comma-separated selection string with range support.

    Accepts formats like "0,2-4,6". Returns deduplicated indices in input order,
    filtering out non-numeric or out-of-bounds values. Returns None if nothing valid.
    """
    seen: set[int] = set()
    result: list[int] = []

    for raw_part in raw.split(","):
        part = raw_part.strip()
        if "-" in part:
            bounds = part.split("-", 1)
            try:
                start, end = int(bounds[0].strip()), int(bounds[1].strip())
            except ValueError:
                continue
            for i in range(start, end + 1):
                if 0 <= i <= max_index and i not in seen:
                    seen.add(i)
                    result.append(i)
        else:
            try:
                i = int(part)
            except ValueError:
                continue
            if 0 <= i <= max_index and i not in seen:
                seen.add(i)
                result.append(i)

    return result if result else None


def select_invoice(invoices: list[Invoice], customer_file: Path) -> list[Invoice]:
    """Interactively select draft invoices to generate.

    - 0 drafts: returns []
    - 1 draft: returns it directly (no prompt)
    - Multiple drafts: displays a numbered list and prompts for all or comma-separated selection
    """
    drafts = [inv for inv in invoices if inv.status == "draft"]

    if not drafts:
        return []

    if len(drafts) == 1:
        return drafts

    drafts.sort(key=lambda inv: inv.date, reverse=True)

    customers = utils.load_customers(customer_file)

    print("Available draft invoices:")
    print("-" * 60)
    for i, inv in enumerate(drafts):
        name = customers[inv.customer_id].address.name if inv.customer_id in customers else str(inv.customer_id)
        print(f"  {i}: {name} - {inv.date} - {inv.total:.2f} EUR")
    print("-" * 60)

    mode = input("Generate all or select specific invoices? [a/s] (default: s): ").strip().lower()

    if mode == "a":
        return drafts

    raw = input("Which invoices should be generated? (e.g. 0,2-4,6): ").strip()
    indices = _parse_selection(raw, len(drafts) - 1)

    if indices is None:
        logger.warning(f"Invalid selection: '{raw}'. No invoices selected.")
        return []

    return [drafts[i] for i in indices]


def _handle_post_generation(result: InvoiceResult, dry_run: bool, open_pdf: bool, open_mail: bool, paths: ProjectPaths):
    """Handle post-generation steps: PDF viewing, email, archiving."""
    if open_pdf:
        try:
            execute_command(["xdg-open", str(result.pdf_path)])
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            logger.warning(f"Could not open PDF viewer: {e}")

    if open_mail:
        thunderbird_command = get_thunderbird()
        if thunderbird_command:
            try:
                execute_command(
                    compose_email(
                        result.invoice,
                        result.config,
                        result.customer,
                        thunderbird_command,
                        result.pdf_path,
                        result.xml_path,
                        dry_run,
                    )
                )
            except (FileNotFoundError, subprocess.CalledProcessError) as e:
                logger.warning(f"Could not open email client: {e}")

    if not dry_run and confirm("Did everything look good and do you want to archive the invoice?"):
        archive_invoice(result.output_file, result.invoice.date.year, paths.out_dir, paths.data_dir)
        store_invoice_parameter(result.invoice, paths.invoice_history_file)
        logger.info("Invoice archived and invoice number saved.")
    else:
        logger.info("Skipping invoice archiving and invoice number saving.")


def invoice_command(
    invoices_path: Annotated[
        Path | None, typer.Option("--invoices", "-i", help="Path to the invoices YAML file.")
    ] = None,
    config_path: Annotated[Path | None, typer.Option("--config", "-c", help="Path to the config YAML file.")] = None,
    customer_path: Annotated[Path | None, typer.Option("--customer", help="Path to the customer CSV file.")] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Custom output path (without extension).")
    ] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Generate without archiving or sending.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable debug logging.")] = False,
    make_all: Annotated[
        bool, typer.Option("--all", help="Generate all invoices without interactive selection.")
    ] = False,
    open_pdf: Annotated[bool, typer.Option("--open-pdf/--no-open-pdf", help="Open the generated PDF.")] = True,
    open_mail: Annotated[
        bool, typer.Option("--open-mail/--no-open-mail", help="Open email client with invoice.")
    ] = True,
):
    """Create one or more invoices."""
    paths = default_project_paths()
    jinja_env = create_jinja_env(paths.template_dir)

    resolved_invoices = invoices_path or resolve_invoices_path(paths.data_dir)
    customer_database = customer_path or paths.invoice_customer_file
    resolved_config = config_path or resolve_config_path(paths.data_dir, paths.project_root)

    logger.debug(f"Using invoices file: {resolved_invoices}")
    logger.debug(f"Using customer database: {customer_database}")
    logger.debug(f"Using config file: {resolved_config}")

    paths_to_validate = [
        (resolved_invoices, "invoices file"),
        (customer_database, "customer database"),
        (resolved_config, "config file"),
    ]
    if not dry_run:
        paths_to_validate.insert(0, (paths.data_dir, "invoice data directory"))

    validate_paths(paths_to_validate)

    config = load_yaml_model(resolved_config, Config)
    all_invoices = load_yaml_model(resolved_invoices, Invoices).invoices

    if dry_run or make_all:
        invoices_to_process = all_invoices
    else:
        invoices_to_process = select_invoice(all_invoices, customer_database)
        if not invoices_to_process:
            logger.info("No draft invoices found.")
            return

    try:
        results = create_invoices(
            invoices_to_process,
            config,
            customer_database,
            dry_run=dry_run,
            paths=paths,
            jinja_env=jinja_env,
            output=output,
        )
    except (OSError, RuntimeError, ValueError) as e:
        logger.error(f"Invoice generation failed: {e}")
        sys.exit(1)

    for result in results:
        if not dry_run:
            try:
                _handle_post_generation(result, dry_run, open_pdf=open_pdf, open_mail=open_mail, paths=paths)
            except OSError as e:
                logger.error(f"Post-generation failed for {result.output_file}: {e}")
        else:
            logger.info("Dry run mode enabled. Skipping post-generation steps.")
            logger.debug(f"Output PDF saved to: {result.pdf_path}")
            logger.debug(f"XRechnung XML saved to: {result.xml_path}")


def print_customer_command(
    file: Annotated[Path | None, typer.Option("--file", "-f", help="Path to the customer CSV file.")] = None,
):
    """Print customer-to-id mapping."""
    if file is None:
        paths = default_project_paths()
        file = paths.invoice_customer_file

    try:
        with file.open("r", encoding="utf-8-sig") as f:
            parsed_file = csv.DictReader(f)
            for customer in parsed_file:
                print(f"{customer['name']}: {customer['customer_id']}")
    except (OSError, csv.Error) as e:
        logger.error(f"Failed to read customer file {file}: {e}")
        sys.exit(1)
