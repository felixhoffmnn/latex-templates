"""CLI utilities: path resolution, validation, confirmations, Thunderbird detection, email composition."""

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from invoice_toolkit.settings import ProjectPaths

if TYPE_CHECKING:
    from invoice_toolkit.invoice.models.customer import Customer
    from invoice_toolkit.invoice.models.invoices import Invoice
    from invoice_toolkit.models import Config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Command execution
# ---------------------------------------------------------------------------


def execute_command(command: list[str]):
    """Run a command as subprocess.

    Raises FileNotFoundError if the command binary is not found,
    and subprocess.CalledProcessError if the command exits non-zero.
    """
    subprocess.run(command, check=True)
    logger.info("Command executed successfully.")


# ---------------------------------------------------------------------------
# Path resolution helpers
# ---------------------------------------------------------------------------


def _find_yaml(directory: Path, stem: str) -> Path | None:
    """Return the first existing YAML file matching *stem* (.yml then .yaml)."""
    for ext in (".yml", ".yaml"):
        candidate = directory / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def resolve_invoices_path(data_dir: Path) -> Path:
    """Resolve invoices file path: INVOICES_PATH env → data_dir/invoices.{yml,yaml}."""
    env = os.getenv("INVOICES_PATH")
    if env:
        return Path(env)
    found = _find_yaml(data_dir, "invoices")
    if found:
        return found
    return data_dir / "invoices.yaml"


def resolve_config_path(data_dir: Path, project_root: Path) -> Path:
    """Resolve config file path: CONFIG_PATH env → data_dir/config.{yml,yaml} → root config.{yml,yaml}."""
    env = os.getenv("CONFIG_PATH")
    if env:
        return Path(env)
    found = _find_yaml(data_dir, "config")
    if found:
        return found
    found = _find_yaml(project_root, "config")
    if found:
        return found
    return project_root / "config.yaml"


def default_project_paths() -> ProjectPaths:
    """Construct a ProjectPaths with CWD-based defaults."""
    project_root = Path.cwd().resolve()
    data_dir = Path(os.getenv("DATA_DIR", str(project_root / "data")))
    return ProjectPaths(
        project_root=project_root,
        data_dir=data_dir,
        out_dir=project_root / "out",
        tmp_dir=project_root / "tmp",
        template_dir=project_root / "template",
        invoice_history_file=data_dir / "invoice.csv",
        invoice_customer_file=data_dir / "customer.csv",
    )


# ---------------------------------------------------------------------------
# Validation & logging
# ---------------------------------------------------------------------------


def validate_paths(paths: list[tuple[Path, str]]):
    """Validate that all required paths exist, logging and exiting if any are missing."""
    missing = [(path, label) for path, label in paths if not path.exists()]
    for path, label in missing:
        logger.error(f"Missing {label}: {path}")
    if missing:
        sys.exit(1)


# ---------------------------------------------------------------------------
# Interactive helpers
# ---------------------------------------------------------------------------


def confirm(prompt: str, default: bool = True) -> bool:
    """Confirm prompt."""
    valid_responses = {"yes": True, "y": True, "no": False, "n": False}
    response_prompt = f"{prompt} [Y/n] " if default else f"{prompt} [y/N] "

    while True:
        choice = input(response_prompt).lower()
        if choice == "":
            return default
        elif choice in valid_responses:
            return valid_responses[choice]
        else:
            print("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")


def get_thunderbird() -> list[str] | None:
    """Check if Thunderbird is installed."""
    candidates = [
        (["thunderbird"], "bare metal"),
        (["flatpak", "run", "org.mozilla.Thunderbird"], "flatpak"),
    ]
    for command, label in candidates:
        try:
            subprocess.run([*command, "--version"], check=True, capture_output=True)
            return command
        except subprocess.CalledProcessError, FileNotFoundError:
            logger.info(f"Thunderbird is not installed as {label}.")

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
) -> list[str]:
    """Compose the mail command.

    This function will compose the mail command that will be executed to open Thunderbird with the mail containing the invoice attached.
    """
    if invoice.due_date is None:
        raise ValueError("Due date must be set.")

    subject = (
        f"{'DRY RUN: ' if dry_run else ''}Rechnung {invoice.invoice_number} vom {invoice.date.strftime('%d.%m.%Y')}"
    )
    inv_num = invoice.invoice_number
    inv_date = invoice.date.strftime("%d.%m.%Y")
    due_date = invoice.due_date.strftime("%d.%m.%Y")
    message = (
        f"<p>Hallo {customer.address.name},</p>"
        f"<p>im Anhang findest du die Rechnung <strong>{inv_num}</strong>"
        f" vom <strong>{inv_date}</strong>.<br>"
        f"Bitte überweise den Betrag bis zum <strong>{due_date}</strong>"
        " auf das angegebene Konto (siehe Rechnung).</p>"
        "<p>Bei Fragen kannst du dich gerne jederzeit melden.</p>"
        f"<p>Viele Grüße<br>{config.sender.address.name}</p>"
    )

    attachments = str(pdf_file.absolute())
    if xml_file.exists():
        attachments += f",{xml_file.absolute()}"

    email_command = [
        *thunderbird_command,
        "-compose",
        f"from='{config.sender.email}',to='{customer.email}',bcc='{config.sender.email}',subject='{subject}',body='{message}',attachment='{attachments}'",
    ]
    logger.debug(f"Email command: {email_command}")

    return email_command
