"""Tests for config models: Address, Bank, Tax, Config validation."""

import pytest
from pydantic import ValidationError

from invoice_toolkit.models import Address, Bank, Config, Invoice


class TestAddress:
    def test_basic_address(self):
        addr = Address(name="John", street="Main St 1", zip="12345", city="Berlin")
        assert addr.name == "John"
        assert addr.zip == "12345"

    @pytest.mark.parametrize(
        ("zip_input", "expected"),
        [
            pytest.param(800, "00800", id="int_padded"),
            pytest.param("0800", "00800", id="string_padded"),
            pytest.param("12345", "12345", id="five_digit_unchanged"),
        ],
    )
    def test_zip_padding(self, zip_input, expected):
        addr = Address(name="John", street="Main St 1", zip=zip_input, city="Berlin")
        assert addr.zip == expected

    @pytest.mark.parametrize(
        "country",
        [
            pytest.param("DE", id="germany"),
            pytest.param("US", id="usa"),
            pytest.param("AT", id="austria"),
            pytest.param("CH", id="switzerland"),
        ],
    )
    def test_country_valid_values(self, country):
        addr = Address(name="John", street="St 1", zip="12345", city="Berlin", country=country)
        assert addr.country == country

    def test_country_invalid_rejected(self):
        with pytest.raises(ValidationError):
            Address(name="John", street="St 1", zip="12345", city="Berlin", country="Deutschland")

    def test_country_optional(self):
        addr = Address(name="John", street="St 1", zip="12345", city="Berlin")
        assert addr.country is None


class TestBank:
    @pytest.mark.parametrize(
        "raw_iban",
        [
            pytest.param("DE89370400440532013000", id="no_spaces"),
            pytest.param("DE89 3704 0044 0532 0130 00", id="canonical_spacing"),
            pytest.param("DE89 37040044 0532013000", id="nonstandard_spacing"),
        ],
    )
    def test_iban_normalized(self, raw_iban):
        bank = Bank(iban=raw_iban, bic="AAAAAAA1BBB", name="Test Bank")
        assert bank.iban == "DE89 3704 0044 0532 0130 00"

    def test_invalid_iban_rejected(self):
        with pytest.raises(ValidationError):
            Bank(iban="INVALID", bic="AAAAAAA1BBB", name="Test Bank")

    def test_invalid_bic_rejected(self):
        with pytest.raises(ValidationError):
            Bank(iban="DE89370400440532013000", bic="invalid", name="Test Bank")


class TestInvoiceConfig:
    @pytest.mark.parametrize(
        "rate",
        [
            pytest.param(0, id="zero"),
            pytest.param(7, id="reduced"),
            pytest.param(19, id="standard"),
        ],
    )
    def test_valid_vat_rates(self, rate):
        inv = Invoice(VAT=rate, due_days=14)  # type: ignore[invalid-argument-type]
        assert inv.default_vat_rate == rate

    def test_invalid_vat_rate_rejected(self):
        with pytest.raises(ValidationError):
            Invoice(VAT=10, due_days=14)  # type: ignore[invalid-argument-type]

    def test_vat_exempt_resets_rate(self):
        inv = Invoice(VAT=19, vat_exempt=True, due_days=14)
        assert inv.default_vat_rate == 0
        assert inv.vat_exempt is True

    def test_populate_by_name(self):
        inv = Invoice(default_vat_rate=19, due_days=14)  # type: ignore[unknown-argument]
        assert inv.default_vat_rate == 19


class TestConfig:
    def _make_config_data(self, **overrides):
        data = {
            "sender": {
                "address": {"name": "Test", "street": "St 1", "zip": "12345", "city": "Berlin"},
                "email": "test@example.com",
                "website": "https://example.com",
                "phone": "+49 176 12345678",
                "tax": {"number": "12 345 6789 0", "office": "Berlin"},
                "bank": {"name": "Test Bank", "iban": "DE89370400440532013000", "bic": "AAAAAAA1BBB"},
            },
            "invoice": {"VAT": 0, "due_days": 14},
        }
        data.update(overrides)
        return data

    def test_full_config(self):
        config = Config(**self._make_config_data())
        assert config.sender.address.name == "Test"
        assert config.invoice.due_days == 14

    def test_config_with_vat(self):
        config = Config(**self._make_config_data(invoice={"VAT": 19, "due_days": 14}))
        assert config.invoice.default_vat_rate == 19
