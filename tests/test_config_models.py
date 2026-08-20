import pytest
from pydantic import ValidationError

from invoice_toolkit.models import Address, Bank, Invoice


def address(**overrides):
    return Address(**({"name": "John", "street": "Main St 1", "zip": "12345", "city": "Berlin"} | overrides))


@pytest.mark.parametrize(("zip_input", "expected"), [(800, "00800"), ("0800", "00800"), ("12345", "12345")])
def test_address_normalizes_zip(zip_input, expected):
    assert address(zip=zip_input).zip == expected


def test_address_country_validation():
    assert address(country="DE").country == "DE"
    assert address().country is None
    with pytest.raises(ValidationError):
        address(country="Deutschland")


@pytest.mark.parametrize(
    "raw_iban",
    ["DE89370400440532013000", "DE89 3704 0044 0532 0130 00", "DE89 37040044 0532013000"],
)
def test_bank_normalizes_iban(raw_iban):
    bank = Bank(iban=raw_iban, bic="AAAAAAA1BBB", name="Test Bank")
    assert bank.iban == "DE89 3704 0044 0532 0130 00"


@pytest.mark.parametrize("overrides", [{"iban": "INVALID"}, {"bic": "invalid"}])
def test_bank_rejects_invalid_identifiers(overrides):
    with pytest.raises(ValidationError):
        Bank(**({"iban": "DE89370400440532013000", "bic": "AAAAAAA1BBB", "name": "Test Bank"} | overrides))


def test_invoice_config_vat_contract():
    assert Invoice(VAT=19, due_days=14).default_vat_rate == 19
    assert Invoice.model_validate({"default_vat_rate": 7, "due_days": 14}).default_vat_rate == 7
    exempt = Invoice(VAT=19, vat_exempt=True, due_days=14)
    assert (exempt.default_vat_rate, exempt.vat_exempt) == (0, True)
    with pytest.raises(ValidationError):
        Invoice.model_validate({"VAT": 10, "due_days": 14})
