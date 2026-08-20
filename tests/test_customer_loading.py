import csv

import pytest

from invoice_toolkit.invoice.utils import load_customer, load_customers

HEADER = ["customer_id", "name", "company", "email", "phone", "url", "buyer_reference", "street", "zip", "city"]
ALICE = [10000, "Alice", "", "alice@example.com", "+49 176 12345678", "", "", "Main St 1", "12345", "Berlin"]
BOB = [
    10001,
    "Bob",
    "Bob Corp",
    "bob@example.com",
    "+49 176 87654321",
    "https://example.com",
    "LEITWEG-999",
    "Side St 2",
    "54321",
    "Munich",
]


def write_customers(path, rows):
    with path.open("w", newline="") as file:
        csv.writer(file).writerows([HEADER, *rows])


def test_load_and_lookup_customers(tmp_path):
    customer_file = tmp_path / "customers.csv"
    write_customers(customer_file, [ALICE, BOB])

    customers = load_customers(customer_file)
    assert set(customers) == {10000, 10001}
    assert (customers[10000].address.name, customers[10000].address.city) == ("Alice", "Berlin")
    assert (customers[10001].company, customers[10001].buyer_reference) == ("Bob Corp", "LEITWEG-999")
    assert str(customers[10001].url) == "https://example.com/"
    assert load_customer(customer_file, "10001") == customers[10001]


def test_load_customers_rejects_duplicates(tmp_path):
    customer_file = tmp_path / "customers.csv"
    write_customers(customer_file, [ALICE, [*ALICE[:1], "Clone", *ALICE[2:]]])
    with pytest.raises(ValueError, match="Duplicate customer IDs"):
        load_customers(customer_file)


def test_load_customer_reports_missing_data(tmp_path):
    customer_file = tmp_path / "customers.csv"
    write_customers(customer_file, [ALICE])
    with pytest.raises(ValueError, match="No customer found"):
        load_customer(customer_file, 99999)
    with pytest.raises(ValueError, match="Failed to load customers"):
        load_customer(tmp_path / "missing.csv", 10000)
