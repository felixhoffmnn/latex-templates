"""Tests for invoice_toolkit/utils.py: build_sender_data, load_yaml_model."""

import pytest
import yaml

from invoice_toolkit.models import Config
from invoice_toolkit.utils import build_sender_data, load_yaml_model


class TestBuildSenderData:
    def _make_config(self):
        return Config(
            sender={  # type: ignore[invalid-argument-type]
                "address": {"name": "Test User", "street": "St 1", "zip": "12345", "city": "Berlin"},
                "email": "test@example.com",
                "website": "https://example.com",
                "phone": "+49 176 12345678",
                "tax": {"number": "12 345 6789 0", "office": "Berlin"},
                "bank": {"name": "Test Bank", "iban": "DE89370400440532013000", "bic": "AAAAAAA1BBB"},
            },
            invoice={"VAT": 0, "due_days": 14},  # type: ignore[invalid-argument-type]
        )

    def test_sender_keys(self):
        config = self._make_config()
        result = build_sender_data(config.sender)
        assert set(result.keys()) == {"sender", "tax", "bank"}

    def test_sender_fields(self):
        config = self._make_config()
        result = build_sender_data(config.sender)
        sender = result["sender"]
        assert sender["name"] == "Test User"
        assert sender["street"] == "St 1"
        assert sender["zip"] == "12345"
        assert sender["city"] == "Berlin"

    def test_phone_cleanup(self):
        config = self._make_config()
        result = build_sender_data(config.sender)
        phone = result["sender"]["phone"]
        assert "tel:" not in phone
        assert "-" not in phone

    def test_email_is_str(self):
        config = self._make_config()
        result = build_sender_data(config.sender)
        assert isinstance(result["sender"]["email"], str)

    def test_website_is_str(self):
        config = self._make_config()
        result = build_sender_data(config.sender)
        assert isinstance(result["sender"]["website"], str)

    def test_tax_fields(self):
        config = self._make_config()
        result = build_sender_data(config.sender)
        assert result["tax"]["office"] == "Berlin"
        assert result["tax"]["number"] == "12 345 6789 0"

    def test_bank_fields(self):
        config = self._make_config()
        result = build_sender_data(config.sender)
        assert result["bank"]["name"] == "Test Bank"
        assert result["bank"]["bic"] == "AAAAAAA1BBB"


class TestLoadConfig:
    def _make_config_yaml(self):
        return {
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

    def test_valid_config(self, tmp_path):
        config_file = tmp_path / "config.yml"
        config_file.write_text(yaml.dump(self._make_config_yaml()))
        config = load_yaml_model(config_file, Config)
        assert config.sender.address.name == "Test"
        assert config.invoice.due_days == 14

    def test_invalid_yaml_raises_value_error(self, tmp_path):
        config_file = tmp_path / "config.yml"
        config_file.write_text("invalid: yaml: [broken")
        with pytest.raises(ValueError, match=r"(?i)Failed to load Config"):
            load_yaml_model(config_file, Config)

    def test_missing_file_raises_value_error(self, tmp_path):
        config_file = tmp_path / "nonexistent.yml"
        with pytest.raises(ValueError, match=r"(?i)Failed to load Config"):
            load_yaml_model(config_file, Config)

    def test_missing_required_fields_raises_value_error(self, tmp_path):
        config_file = tmp_path / "config.yml"
        config_file.write_text(yaml.dump({"sender": {}}))
        with pytest.raises(ValueError, match=r"(?i)Failed to load Config"):
            load_yaml_model(config_file, Config)

    def test_empty_file_raises_value_error(self, tmp_path):
        config_file = tmp_path / "config.yml"
        config_file.write_text("")
        with pytest.raises(ValueError, match=r"(?i)Failed to load Config"):
            load_yaml_model(config_file, Config)
