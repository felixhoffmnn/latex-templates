from unittest.mock import patch

import pytest

from invoice_toolkit.letter.models.letter import Letter
from invoice_toolkit.letter.utils import load_letter
from invoice_toolkit.models import Address

FRONTMATTER = """recipient:
  name: Max Mustermann
  street: Musterstraße 1
  zip: '12345'
  city: Berlin
subject: Kündigung"""


def write_letter(path, frontmatter=FRONTMATTER, body="Hello **world**"):
    path.write_text(f"---\n{frontmatter}\n---\n{body}", encoding="utf-8")


def test_letter_defaults_and_overrides():
    recipient = Address(name="Max", street="Main 1", zip="12345", city="Berlin")
    default = Letter(recipient=recipient, subject="Test")
    custom = Letter(recipient=recipient, subject="Test", opening="Hallo,", closing="Viele Grüße,")
    assert (default.opening, default.closing) == (
        "Sehr geehrte Damen und Herren,",
        "Mit freundlichen Grüßen,",
    )
    assert (custom.opening, custom.closing) == ("Hallo,", "Viele Grüße,")


def test_load_letter(tmp_path):
    letter_file = tmp_path / "letter.md"
    write_letter(letter_file)
    with patch("pypandoc.convert_text", return_value="Hello *world*"):
        letter, content = load_letter(letter_file)
    assert (letter.subject, letter.recipient.name, content) == ("Kündigung", "Max Mustermann", "Hello *world*")


@pytest.mark.parametrize(
    "content",
    [
        "no frontmatter here",
        "---\ninvalid: yaml: [broken\n---\nbody",
        "---\nsubject: Test\n---\nbody",
    ],
)
def test_load_letter_rejects_invalid_frontmatter(tmp_path, content):
    letter_file = tmp_path / "letter.md"
    letter_file.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        load_letter(letter_file)


def test_load_letter_reports_io_and_pandoc_failures(tmp_path):
    with pytest.raises(OSError, match="Failed to read letter file"):
        load_letter(tmp_path / "missing.md")

    letter_file = tmp_path / "letter.md"
    write_letter(letter_file)
    with (
        patch("pypandoc.convert_text", side_effect=RuntimeError("pandoc failed")),
        pytest.raises(RuntimeError, match="Pandoc conversion failed"),
    ):
        load_letter(letter_file)
