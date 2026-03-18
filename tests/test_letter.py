"""Tests for letter models and load_letter utility."""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from invoice_toolkit.letter.models.letter import Letter, Location
from invoice_toolkit.letter.utils import load_letter
from invoice_toolkit.models import Address

# ---------------------------------------------------------------------------
# Location model
# ---------------------------------------------------------------------------


class TestLocation:
    def test_string_value(self):
        loc = Location(key="Projekt", value="Website Relaunch")
        assert loc.key == "Projekt"
        assert loc.value == "Website Relaunch"

    def test_int_value(self):
        loc = Location(key="Kundennummer", value=12345)
        assert loc.value == 12345

    def test_missing_key_rejected(self):
        with pytest.raises(ValidationError):
            Location(value="test")  # type: ignore[missing-argument]

    def test_missing_value_rejected(self):
        with pytest.raises(ValidationError):
            Location(key="test")  # type: ignore[missing-argument]


# ---------------------------------------------------------------------------
# Letter model
# ---------------------------------------------------------------------------


def _make_address(**overrides):
    defaults = {"name": "Max Mustermann", "street": "Musterstraße 1", "zip": "12345", "city": "Berlin"}
    defaults.update(overrides)
    return defaults


class TestLetter:
    def test_required_fields(self):
        letter = Letter(recipient=_make_address(), subject="Kündigung")
        assert letter.subject == "Kündigung"
        assert isinstance(letter.recipient, Address)

    def test_default_opening(self):
        letter = Letter(recipient=_make_address(), subject="Test")
        assert letter.opening == "Sehr geehrte Damen und Herren,"

    def test_default_closing(self):
        letter = Letter(recipient=_make_address(), subject="Test")
        assert letter.closing == "Mit freundlichen Grüßen,"

    def test_custom_opening_closing(self):
        letter = Letter(
            recipient=_make_address(),
            subject="Test",
            opening="Liebe Kolleginnen,",
            closing="Herzliche Grüße,",
        )
        assert letter.opening == "Liebe Kolleginnen,"
        assert letter.closing == "Herzliche Grüße,"

    def test_optional_location(self):
        letter = Letter(
            recipient=_make_address(),
            subject="Test",
            location=[Location(key="Projekt", value="Alpha")],
        )
        assert letter.location is not None and len(letter.location) == 1

    def test_optional_place(self):
        letter = Letter(recipient=_make_address(), subject="Test", place="München")
        assert letter.place == "München"

    def test_location_defaults_to_none(self):
        letter = Letter(recipient=_make_address(), subject="Test")
        assert letter.location is None

    def test_place_defaults_to_none(self):
        letter = Letter(recipient=_make_address(), subject="Test")
        assert letter.place is None

    def test_missing_recipient_rejected(self):
        with pytest.raises(ValidationError):
            Letter(subject="Test")  # type: ignore[missing-argument]

    def test_missing_subject_rejected(self):
        with pytest.raises(ValidationError):
            Letter(recipient=_make_address())  # type: ignore[missing-argument]


# ---------------------------------------------------------------------------
# load_letter
# ---------------------------------------------------------------------------


class TestLoadLetter:
    def _write_letter(self, path, frontmatter, body):
        path.write_text(f"---\n{frontmatter}\n---\n{body}", encoding="utf-8")

    def _valid_frontmatter(self):
        return (
            "recipient:\n"
            "  name: Max Mustermann\n"
            "  street: Musterstraße 1\n"
            "  zip: '12345'\n"
            "  city: Berlin\n"
            "subject: Kündigung"
        )

    def test_valid_letter(self, tmp_path):
        letter_file = tmp_path / "letter.md"
        self._write_letter(letter_file, self._valid_frontmatter(), "Hello **world**")

        with patch("pypandoc.convert_text", return_value="Hello *world*"):
            letter, content = load_letter(letter_file)

        assert letter.subject == "Kündigung"
        assert letter.recipient.name == "Max Mustermann"
        assert content == "Hello *world*"

    def test_missing_delimiters_raises_value_error(self, tmp_path):
        letter_file = tmp_path / "letter.md"
        letter_file.write_text("no frontmatter here", encoding="utf-8")

        with pytest.raises(ValueError, match="Invalid frontmatter"):
            load_letter(letter_file)

    def test_invalid_yaml_raises_value_error(self, tmp_path):
        letter_file = tmp_path / "letter.md"
        self._write_letter(letter_file, "invalid: yaml: [broken", "body")

        with pytest.raises(ValueError, match="Failed to parse frontmatter"):
            load_letter(letter_file)

    def test_missing_file_raises_os_error(self, tmp_path):
        with pytest.raises(OSError, match="Failed to read letter file"):
            load_letter(tmp_path / "nonexistent.md")

    def test_pandoc_failure_raises_runtime_error(self, tmp_path):
        letter_file = tmp_path / "letter.md"
        self._write_letter(letter_file, self._valid_frontmatter(), "some body")

        with (
            patch("pypandoc.convert_text", side_effect=RuntimeError("pandoc failed")),
            pytest.raises(RuntimeError, match="Pandoc conversion failed"),
        ):
            load_letter(letter_file)

    def test_missing_required_letter_fields_raises_value_error(self, tmp_path):
        letter_file = tmp_path / "letter.md"
        self._write_letter(letter_file, "subject: Test", "body")

        with pytest.raises(ValueError, match="Failed to parse frontmatter"):
            load_letter(letter_file)
