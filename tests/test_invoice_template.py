import csv
from itertools import count
from unittest.mock import patch

from factories import make_config, make_customer, make_invoice

from invoice_toolkit.invoice.template import (
    _build_invoice_data,
    _prepare_vat_context,
    _resolve_vat,
    archive_invoice,
    get_invoice_id,
    setup_csv_archive,
    store_invoice_parameter,
)

CSV_HEADER = ["invoice_id", "customer_id", "date", "total", "status"]


def write_csv(path, rows):
    with path.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(CSV_HEADER)
        writer.writerows(rows)


def read_csv(path):
    with path.open() as file:
        return list(csv.reader(file))


def test_setup_csv_archive_is_idempotent(tmp_path):
    archive = tmp_path / "invoice.csv"
    setup_csv_archive(archive)
    assert read_csv(archive) == [CSV_HEADER]
    with archive.open("a") as file:
        file.write("1,10000,2025-01-01,100,sent\n")
    setup_csv_archive(archive)
    assert len(read_csv(archive)) == 2


def test_get_invoice_id_contract(tmp_path, env_cleanup):
    archive = tmp_path / "invoice.csv"
    assert get_invoice_id(False, archive) == 1

    write_csv(
        archive,
        [
            ["broken", 10000, "2025-01-01", 100, "sent"],
            [5, 10000, "2025-01-01", 100, "sent"],
            [10, 10001, "2025-02-01", 200, "sent"],
        ],
    )
    assert get_invoice_id(False, archive) == 11

    dry_run_counter = count(3)
    assert [get_invoice_id(True, archive, dry_run_counter) for _ in range(2)] == [3, 4]

    write_csv(archive, [])
    with patch.dict("os.environ", {"LAST_INVOICE": "42"}):
        assert get_invoice_id(False, archive) == 42


def test_store_invoice_parameter_uses_billable_total(tmp_path):
    net_archive = tmp_path / "net.csv"
    net_invoice = make_invoice(invoice_id=1)
    store_invoice_parameter(net_invoice, net_archive)
    assert read_csv(net_archive)[1] == ["1", "10000", "2025-06-15", "50.0", "sent"]

    gross_archive = tmp_path / "gross.csv"
    gross_invoice = make_invoice(invoice_id=2)
    gross_invoice.total_vat = 9.5
    gross_invoice.total_gross = gross_invoice.total + gross_invoice.total_vat
    store_invoice_parameter(gross_invoice, gross_archive)
    assert read_csv(gross_archive)[1][3] == "59.5"


def test_archive_invoice_moves_available_outputs(tmp_path):
    out_dir = tmp_path / "out"
    data_dir = tmp_path / "data"
    invoice_out = out_dir / "invoice"
    invoice_out.mkdir(parents=True)

    for filename in ("RE0001.pdf", "RE0001.xml", "RE0002.pdf"):
        (invoice_out / filename).write_text("content")

    archive_invoice("RE0001", 2025, out_dir, data_dir)
    archive_invoice("RE0002", 2024, out_dir, data_dir)

    assert {(data_dir / "archive" / "2025" / name).exists() for name in ("RE0001.pdf", "RE0001.xml")} == {True}
    assert (data_dir / "archive" / "2024" / "RE0002.pdf").exists()
    assert not (data_dir / "archive" / "2024" / "RE0002.xml").exists()
    assert not any(invoice_out.iterdir())


def test_invoice_template_data_contract():
    invoice = make_invoice()
    config = make_config()
    customer = make_customer(company="Customer GmbH")
    _resolve_vat(invoice, vat_exempt=False, default_vat_rate=19)

    data = _build_invoice_data(invoice, config, customer, _prepare_vat_context(invoice, False))

    assert data["invoice"]["date"] == "15.06.2025"
    assert data["invoice"]["due_date"] == "15.07.2025"
    assert data["invoice"]["items"][0]["vat_rate"] == 19
    assert data["recipient"] == {
        "name": "Kunde Name",
        "extra": None,
        "street": "Kundenstr. 1",
        "zip": "54321",
        "city": "Munich",
        "company": "Customer GmbH",
    }
    assert set(data["config"]["sender"]) == {"name", "street", "zip", "city", "phone", "email", "website"}
