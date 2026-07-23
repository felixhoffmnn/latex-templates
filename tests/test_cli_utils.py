from pathlib import Path
from unittest.mock import patch

import pytest
from factories import make_config, make_customer, make_invoice

from invoice_toolkit.cli.utils import (
    _find_yaml,
    compose_email,
    get_thunderbird,
    resolve_config_path,
    resolve_invoices_path,
    validate_paths,
)


def test_find_yaml_prefers_yml(tmp_path):
    assert _find_yaml(tmp_path, "invoices") is None
    yaml_file = tmp_path / "invoices.yaml"
    yaml_file.touch()
    assert _find_yaml(tmp_path, "invoices") == yaml_file
    yml_file = tmp_path / "invoices.yml"
    yml_file.touch()
    assert _find_yaml(tmp_path, "invoices") == yml_file


def test_resolve_invoices_path_precedence(tmp_path, env_cleanup):
    assert resolve_invoices_path(tmp_path) == tmp_path / "invoices.yaml"
    yaml_file = tmp_path / "invoices.yaml"
    yaml_file.touch()
    assert resolve_invoices_path(tmp_path) == yaml_file
    yml_file = tmp_path / "invoices.yml"
    yml_file.touch()
    assert resolve_invoices_path(tmp_path) == yml_file
    with patch.dict("os.environ", {"INVOICES_PATH": "/custom/invoices.yml"}):
        assert resolve_invoices_path(tmp_path) == Path("/custom/invoices.yml")


def test_resolve_config_path_precedence(tmp_path, env_cleanup):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    assert resolve_config_path(data_dir, tmp_path) == tmp_path / "config.yaml"

    root_config = tmp_path / "config.yaml"
    root_config.touch()
    assert resolve_config_path(data_dir, tmp_path) == root_config

    data_config = data_dir / "config.yml"
    data_config.touch()
    assert resolve_config_path(data_dir, tmp_path) == data_config

    with patch.dict("os.environ", {"CONFIG_PATH": "/custom/config.yml"}):
        assert resolve_config_path(data_dir, tmp_path) == Path("/custom/config.yml")


def test_validate_paths(tmp_path):
    existing = tmp_path / "exists"
    existing.touch()
    validate_paths([(existing, "existing file")])
    with pytest.raises(SystemExit) as error:
        validate_paths([(tmp_path / "missing", "missing file")])
    assert error.value.code == 1


def test_get_thunderbird_fallbacks():
    with patch("invoice_toolkit.cli.utils.subprocess.run"):
        assert get_thunderbird() == ["thunderbird"]
    with patch("invoice_toolkit.cli.utils.subprocess.run", side_effect=[FileNotFoundError, None]):
        assert get_thunderbird() == ["flatpak", "run", "org.mozilla.Thunderbird"]
    with patch("invoice_toolkit.cli.utils.subprocess.run", side_effect=FileNotFoundError):
        assert get_thunderbird() is None


def test_compose_email_contract(tmp_path):
    pdf = tmp_path / "RE0001.pdf"
    xml = tmp_path / "RE0001.xml"
    pdf.touch()
    invoice = make_invoice()

    command = compose_email(invoice, make_config(), make_customer(), ["thunderbird"], pdf, xml)
    assert command[:2] == ["thunderbird", "-compose"]
    assert "Rechnung RE0001" in command[2]
    assert "Kunde Name" in command[2]
    assert str(pdf.absolute()) in command[2]
    assert str(xml.absolute()) not in command[2]

    xml.touch()
    assert str(xml.absolute()) in compose_email(invoice, make_config(), make_customer(), ["thunderbird"], pdf, xml)[2]

    with pytest.raises(ValueError, match="Due date must be set"):
        compose_email(make_invoice(due_date=None), make_config(), make_customer(), ["thunderbird"], pdf, xml)
