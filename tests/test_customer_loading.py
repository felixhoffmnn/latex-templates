"""Tests for customer CSV loading and lookup."""

import csv
from typing import TYPE_CHECKING

import pytest

from invoice_toolkit.invoice.utils import load_customer, load_customers

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def customer_csv(tmp_path) -> Path:
    """Create a minimal customer CSV file."""
    csv_file = tmp_path / "customers.csv"
    with csv_file.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["customer_id", "name", "company", "email", "phone", "url", "buyer_reference", "street", "zip", "city"]
        )
        writer.writerow(
            [10000, "Alice", "", "alice@example.com", "+49 176 12345678", "", "", "Main St 1", "12345", "Berlin"]
        )
        writer.writerow(
            [
                10001,
                "Bob",
                "Bob Corp",
                "bob@example.com",
                "+49 176 87654321",
                "",
                "LEITWEG-999",
                "Side St 2",
                "54321",
                "Munich",
            ]
        )
    return csv_file


@pytest.fixture()
def duplicate_csv(tmp_path) -> Path:
    """Create a CSV with duplicate customer IDs."""
    csv_file = tmp_path / "dup_customers.csv"
    with csv_file.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["customer_id", "name", "company", "email", "phone", "url", "buyer_reference", "street", "zip", "city"]
        )
        writer.writerow(
            [10000, "Alice", "", "alice@example.com", "+49 176 12345678", "", "", "Main St 1", "12345", "Berlin"]
        )
        writer.writerow(
            [10000, "Clone", "", "clone@example.com", "+49 176 11111111", "", "", "Clone St", "11111", "Hamburg"]
        )
    return csv_file


class TestLoadCustomers:
    def test_load_all(self, customer_csv):
        customers = load_customers(customer_csv)
        assert len(customers) == 2
        assert 10000 in customers
        assert 10001 in customers

    def test_customer_fields(self, customer_csv):
        customers = load_customers(customer_csv)
        alice = customers[10000]
        assert alice.address.name == "Alice"
        assert alice.address.city == "Berlin"

    def test_company_field(self, customer_csv):
        customers = load_customers(customer_csv)
        bob = customers[10001]
        assert bob.company == "Bob Corp"

    def test_buyer_reference(self, customer_csv):
        customers = load_customers(customer_csv)
        bob = customers[10001]
        assert bob.buyer_reference == "LEITWEG-999"

    def test_duplicate_ids_rejected(self, duplicate_csv):
        with pytest.raises(ValueError, match="Duplicate customer IDs"):
            load_customers(duplicate_csv)


class TestLoadCustomer:
    def test_load_by_id(self, customer_csv):
        customer = load_customer(customer_csv, 10000)
        assert customer.address.name == "Alice"

    def test_load_by_string_id(self, customer_csv):
        customer = load_customer(customer_csv, "10001")
        assert customer.address.name == "Bob"

    def test_missing_id_raises(self, customer_csv):
        with pytest.raises(ValueError, match="No customer found"):
            load_customer(customer_csv, 99999)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises((FileNotFoundError, ValueError)):
            load_customer(tmp_path / "nonexistent.csv", 10000)
