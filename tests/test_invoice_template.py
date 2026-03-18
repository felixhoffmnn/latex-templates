"""Tests for invoice_toolkit/invoice/template.py: setup_csv_archive, get_invoice_id, store_invoice_parameter, archive_invoice."""

from __future__ import annotations

import csv
from typing import TYPE_CHECKING
from unittest.mock import patch

from factories import make_invoice as _base_make_invoice

import invoice_toolkit.invoice.template as tpl
from invoice_toolkit.invoice.template import (
    archive_invoice,
    get_invoice_id,
    setup_csv_archive,
    store_invoice_parameter,
)

if TYPE_CHECKING:
    from pathlib import Path

CSV_HEADER = ["invoice_id", "customer_id", "date", "total", "status"]


def _make_invoice(invoice_id=1, total_vat=0.0, **kwargs):
    kwargs.setdefault("invoice_number", f"RE{invoice_id:04d}")
    inv = _base_make_invoice(invoice_id=invoice_id, **kwargs)
    inv.total_vat = total_vat
    if total_vat > 0:
        inv.total_gross = inv.total + total_vat
    return inv


def _write_csv(path: Path, rows: list[list]):
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        for row in rows:
            writer.writerow(row)


def _read_csv_rows(path: Path) -> list[list[str]]:
    with path.open("r") as f:
        reader = csv.reader(f)
        return list(reader)


# ---------------------------------------------------------------------------
# setup_csv_archive
# ---------------------------------------------------------------------------


class TestSetupCsvArchive:
    def test_creates_file_with_header(self, tmp_path):
        csv_file = tmp_path / "invoice.csv"
        setup_csv_archive(csv_file)
        rows = _read_csv_rows(csv_file)
        assert len(rows) == 1
        assert rows[0] == CSV_HEADER

    def test_does_not_overwrite_existing(self, tmp_path):
        csv_file = tmp_path / "invoice.csv"
        _write_csv(csv_file, [[1, 10000, "2025-01-01", 100, "sent"]])
        setup_csv_archive(csv_file)
        rows = _read_csv_rows(csv_file)
        assert len(rows) == 2  # header + 1 data row


# ---------------------------------------------------------------------------
# get_invoice_id
# ---------------------------------------------------------------------------


class TestGetInvoiceId:
    def test_csv_with_existing_invoices(self, tmp_path):
        csv_file = tmp_path / "invoice.csv"
        _write_csv(
            csv_file,
            [
                [5, 10000, "2025-01-01", 100, "sent"],
                [10, 10001, "2025-02-01", 200, "sent"],
            ],
        )
        result = get_invoice_id(dry_run=False, history_file=csv_file)
        assert result == 11

    def test_empty_csv_returns_custom_last_invoice(self, tmp_path):
        csv_file = tmp_path / "invoice.csv"
        _write_csv(csv_file, [])
        with patch.dict("os.environ", {"LAST_INVOICE": "100"}):
            result = get_invoice_id(dry_run=False, history_file=csv_file)
        assert result == 100

    def test_missing_csv_creates_and_returns_custom(self, tmp_path):
        csv_file = tmp_path / "invoice.csv"
        with patch.dict("os.environ", {"LAST_INVOICE": "42"}):
            result = get_invoice_id(dry_run=False, history_file=csv_file)
        assert result == 42
        assert csv_file.exists()

    def test_dry_run_increments_counter(self, tmp_path):
        tpl._dry_run_counter = 0
        csv_file = tmp_path / "invoice.csv"

        with patch.dict("os.environ", {"LAST_INVOICE": "1"}):
            first = get_invoice_id(dry_run=True, history_file=csv_file)
            second = get_invoice_id(dry_run=True, history_file=csv_file)

        assert first == 1
        assert second == 2

        # Reset to avoid leaking state
        tpl._dry_run_counter = 0

    def test_last_invoice_env_var_override(self, tmp_path):
        csv_file = tmp_path / "invoice.csv"
        _write_csv(csv_file, [])
        with patch.dict("os.environ", {"LAST_INVOICE": "500"}):
            result = get_invoice_id(dry_run=False, history_file=csv_file)
        assert result == 500

    def test_malformed_rows_skipped(self, tmp_path):
        csv_file = tmp_path / "invoice.csv"
        with csv_file.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)
            writer.writerow(["not_a_number", 10000, "2025-01-01", 100, "sent"])
            writer.writerow([5, 10000, "2025-01-01", 200, "sent"])
        result = get_invoice_id(dry_run=False, history_file=csv_file)
        assert result == 6

    def test_default_last_invoice_is_1(self, tmp_path, env_cleanup):
        csv_file = tmp_path / "invoice.csv"
        _write_csv(csv_file, [])
        result = get_invoice_id(dry_run=False, history_file=csv_file)
        assert result == 1


# ---------------------------------------------------------------------------
# store_invoice_parameter
# ---------------------------------------------------------------------------


class TestStoreInvoiceParameter:
    def test_appends_row_to_csv(self, tmp_path):
        csv_file = tmp_path / "invoice.csv"
        _write_csv(csv_file, [])
        inv = _make_invoice(invoice_id=42)
        store_invoice_parameter(inv, csv_file)
        rows = _read_csv_rows(csv_file)
        assert len(rows) == 2  # header + 1 data row
        assert rows[1][0] == "42"

    def test_creates_csv_if_missing(self, tmp_path):
        csv_file = tmp_path / "invoice.csv"
        inv = _make_invoice(invoice_id=1)
        store_invoice_parameter(inv, csv_file)
        assert csv_file.exists()
        rows = _read_csv_rows(csv_file)
        assert len(rows) == 2

    def test_uses_total_gross_when_vat_positive(self, tmp_path):
        csv_file = tmp_path / "invoice.csv"
        _write_csv(csv_file, [])
        inv = _make_invoice(invoice_id=1, total_vat=9.5)
        store_invoice_parameter(inv, csv_file)
        rows = _read_csv_rows(csv_file)
        assert float(rows[1][3]) == inv.total_gross

    def test_uses_total_when_no_vat(self, tmp_path):
        csv_file = tmp_path / "invoice.csv"
        _write_csv(csv_file, [])
        inv = _make_invoice(invoice_id=1, total_vat=0.0)
        store_invoice_parameter(inv, csv_file)
        rows = _read_csv_rows(csv_file)
        assert float(rows[1][3]) == inv.total

    def test_date_formatted_as_iso(self, tmp_path):
        csv_file = tmp_path / "invoice.csv"
        _write_csv(csv_file, [])
        inv = _make_invoice(invoice_id=1)
        store_invoice_parameter(inv, csv_file)
        rows = _read_csv_rows(csv_file)
        assert rows[1][2] == "2025-06-15"

    def test_status_always_sent(self, tmp_path):
        csv_file = tmp_path / "invoice.csv"
        _write_csv(csv_file, [])
        inv = _make_invoice(invoice_id=1)
        store_invoice_parameter(inv, csv_file)
        rows = _read_csv_rows(csv_file)
        assert rows[1][4] == "sent"


# ---------------------------------------------------------------------------
# archive_invoice
# ---------------------------------------------------------------------------


class TestArchiveInvoice:
    def _setup_files(self, tmp_path, output_file, extensions=(".pdf", ".xml")):
        out_dir = tmp_path / "out"
        data_dir = tmp_path / "data"
        invoice_out = out_dir / "invoice"
        invoice_out.mkdir(parents=True)
        for ext in extensions:
            (invoice_out / (output_file + ext)).write_text("content")
        return out_dir, data_dir

    def test_both_pdf_and_xml_moved(self, tmp_path):
        out_dir, data_dir = self._setup_files(tmp_path, "RE0001_20250615_10000")
        archive_invoice("RE0001_20250615_10000", 2025, out_dir, data_dir)
        archive_dir = data_dir / "archive" / "2025"
        assert (archive_dir / "RE0001_20250615_10000.pdf").exists()
        assert (archive_dir / "RE0001_20250615_10000.xml").exists()
        assert not (out_dir / "invoice" / "RE0001_20250615_10000.pdf").exists()

    def test_only_pdf_no_xml(self, tmp_path):
        out_dir, data_dir = self._setup_files(tmp_path, "RE0001_20250615_10000", extensions=(".pdf",))
        archive_invoice("RE0001_20250615_10000", 2025, out_dir, data_dir)
        archive_dir = data_dir / "archive" / "2025"
        assert (archive_dir / "RE0001_20250615_10000.pdf").exists()
        assert not (archive_dir / "RE0001_20250615_10000.xml").exists()

    def test_archive_directory_created_with_parents(self, tmp_path):
        out_dir, data_dir = self._setup_files(tmp_path, "RE0001_20250615_10000")
        assert not data_dir.exists()
        archive_invoice("RE0001_20250615_10000", 2025, out_dir, data_dir)
        assert (data_dir / "archive" / "2025").is_dir()

    def test_year_based_subdirectory(self, tmp_path):
        out_dir, data_dir = self._setup_files(tmp_path, "RE0001_20230101_10000")
        archive_invoice("RE0001_20230101_10000", 2023, out_dir, data_dir)
        assert (data_dir / "archive" / "2023").is_dir()
