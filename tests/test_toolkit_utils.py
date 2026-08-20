import pytest
import yaml
from factories import make_config

from invoice_toolkit.models import Config
from invoice_toolkit.utils import build_sender_data, load_yaml_model


def test_build_sender_data_contract():
    assert build_sender_data(make_config().sender) == {
        "sender": {
            "name": "Sender Name",
            "street": "St 1",
            "zip": "12345",
            "city": "Berlin",
            "phone": "+49 176 12345678",
            "email": "sender@example.com",
            "website": "https://example.com/",
        },
        "tax": {"office": "Berlin", "number": "12 345 6789 0"},
        "bank": {
            "iban": "DE89 3704 0044 0532 0130 00",
            "bic": "AAAAAAA1BBB",
            "name": "Test Bank",
        },
    }


def test_load_yaml_model(tmp_path):
    config_file = tmp_path / "config.yml"
    config_file.write_text(yaml.safe_dump(make_config().model_dump(mode="json", by_alias=True)))
    config = load_yaml_model(config_file, Config)
    assert (config.sender.address.name, config.invoice.due_days) == ("Sender Name", 14)


@pytest.mark.parametrize("content", ["invalid: yaml: [broken", "{}", ""])
def test_load_yaml_model_rejects_invalid_content(tmp_path, content):
    config_file = tmp_path / "config.yml"
    config_file.write_text(content)
    with pytest.raises(ValueError, match="Failed to load Config"):
        load_yaml_model(config_file, Config)


def test_load_yaml_model_reports_missing_file(tmp_path):
    with pytest.raises(ValueError, match="Failed to load Config"):
        load_yaml_model(tmp_path / "missing.yml", Config)
