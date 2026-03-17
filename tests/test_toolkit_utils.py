"""Tests for invoice_toolkit/utils.py: _currency_filter, create_jinja_env, load_yaml_model."""

import pytest
import yaml

from invoice_toolkit.models import Config
from invoice_toolkit.utils import _currency_filter, create_jinja_env, load_yaml_model


class TestCurrencyFilter:
    def test_german_locale_default(self):
        assert _currency_filter(1234.56) == "1.234,56"

    def test_german_locale_explicit(self):
        assert _currency_filter(1234.56, locale="de") == "1.234,56"

    def test_german_locale_zero(self):
        assert _currency_filter(0.0) == "0,00"

    def test_german_locale_large_number(self):
        assert _currency_filter(1000000.0) == "1.000.000,00"

    def test_german_locale_small_decimal(self):
        assert _currency_filter(0.99) == "0,99"

    def test_german_locale_rounds_to_two_decimals(self):
        assert _currency_filter(1.999) == "2,00"

    def test_english_locale(self):
        assert _currency_filter(1234.56, locale="en") == "1234.56"

    def test_english_locale_zero(self):
        assert _currency_filter(0.0, locale="en") == "0.00"

    def test_english_locale_large_number(self):
        assert _currency_filter(1000000.0, locale="en") == "1000000.00"

    def test_integer_input(self):
        assert _currency_filter(100) == "100,00"


class TestCreateJinjaEnv:
    def test_returns_environment(self, tmp_path):
        env = create_jinja_env(tmp_path)
        assert env is not None

    def test_trim_blocks_enabled(self, tmp_path):
        env = create_jinja_env(tmp_path)
        assert env.trim_blocks is True

    def test_autoescape_disabled(self, tmp_path):
        env = create_jinja_env(tmp_path)
        assert env.autoescape is False

    def test_currency_filter_registered(self, tmp_path):
        env = create_jinja_env(tmp_path)
        assert "currency" in env.filters
        currency_filter = env.filters["currency"]
        assert currency_filter(1234.56) == "1.234,56"  # type: ignore[call-arg]

    def test_template_rendering(self, tmp_path):
        (tmp_path / "test.txt").write_text("Price: {{ value | currency }}")
        env = create_jinja_env(tmp_path)
        template = env.get_template("test.txt")
        assert template.render(value=42.5) == "Price: 42,50"


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
