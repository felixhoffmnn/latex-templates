"""Tests for invoice_cli/utils.py: path resolution, validate_paths, confirm, get_thunderbird, compose_email."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from factories import make_config, make_customer, make_invoice

from invoice_toolkit.cli.utils import (
    _find_yaml,
    compose_email,
    confirm,
    get_thunderbird,
    resolve_config_path,
    resolve_invoices_path,
    validate_paths,
)

# ---------------------------------------------------------------------------
# _find_yaml
# ---------------------------------------------------------------------------


class TestFindYaml:
    def test_yml_exists(self, tmp_path):
        (tmp_path / "invoices.yml").touch()
        assert _find_yaml(tmp_path, "invoices") == tmp_path / "invoices.yml"

    def test_yaml_exists(self, tmp_path):
        (tmp_path / "invoices.yaml").touch()
        assert _find_yaml(tmp_path, "invoices") == tmp_path / "invoices.yaml"

    def test_yml_preferred_over_yaml(self, tmp_path):
        (tmp_path / "invoices.yml").touch()
        (tmp_path / "invoices.yaml").touch()
        assert _find_yaml(tmp_path, "invoices") == tmp_path / "invoices.yml"

    def test_neither_returns_none(self, tmp_path):
        assert _find_yaml(tmp_path, "invoices") is None


# ---------------------------------------------------------------------------
# resolve_invoices_path
# ---------------------------------------------------------------------------


class TestResolveInvoicesPath:
    def test_env_var_takes_priority(self, tmp_path):
        with patch.dict("os.environ", {"INVOICES_PATH": "/custom/invoices.yml"}):
            result = resolve_invoices_path(tmp_path)
        assert result == Path("/custom/invoices.yml")

    def test_yml_file_found(self, tmp_path):
        (tmp_path / "invoices.yml").touch()
        with patch.dict("os.environ", {}, clear=True):
            os.environ.pop("INVOICES_PATH", None)
            result = resolve_invoices_path(tmp_path)
        assert result == tmp_path / "invoices.yml"

    def test_yaml_file_found(self, tmp_path):
        (tmp_path / "invoices.yaml").touch()
        with patch.dict("os.environ", {}, clear=True):
            os.environ.pop("INVOICES_PATH", None)
            result = resolve_invoices_path(tmp_path)
        assert result == tmp_path / "invoices.yaml"

    def test_fallback_default(self, tmp_path):
        with patch.dict("os.environ", {}, clear=True):
            os.environ.pop("INVOICES_PATH", None)
            result = resolve_invoices_path(tmp_path)
        assert result == tmp_path / "invoices.yaml"


# ---------------------------------------------------------------------------
# resolve_config_path
# ---------------------------------------------------------------------------


class TestResolveConfigPath:
    def test_env_var_takes_priority(self, tmp_path):
        with patch.dict("os.environ", {"CONFIG_PATH": "/custom/config.yml"}):
            result = resolve_config_path(tmp_path / "data", tmp_path)
        assert result == Path("/custom/config.yml")

    def test_data_dir_config_found(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "config.yml").touch()
        with patch.dict("os.environ", {}, clear=True):
            os.environ.pop("CONFIG_PATH", None)
            result = resolve_config_path(data_dir, tmp_path)
        assert result == data_dir / "config.yml"

    def test_project_root_config_found(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (tmp_path / "config.yaml").touch()
        with patch.dict("os.environ", {}, clear=True):
            os.environ.pop("CONFIG_PATH", None)
            result = resolve_config_path(data_dir, tmp_path)
        assert result == tmp_path / "config.yaml"

    def test_fallback_default(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        with patch.dict("os.environ", {}, clear=True):
            os.environ.pop("CONFIG_PATH", None)
            result = resolve_config_path(data_dir, tmp_path)
        assert result == tmp_path / "config.yaml"


# ---------------------------------------------------------------------------
# validate_paths
# ---------------------------------------------------------------------------


class TestValidatePaths:
    def test_all_paths_exist(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.touch()
        f2.touch()
        validate_paths([(f1, "file a"), (f2, "file b")])  # should not exit

    def test_missing_path_exits(self, tmp_path):
        missing = tmp_path / "nonexistent.txt"
        with pytest.raises(SystemExit) as exc_info:
            validate_paths([(missing, "missing file")])
        assert exc_info.value.code == 1

    def test_multiple_missing_logs_each(self, tmp_path):
        m1 = tmp_path / "a.txt"
        m2 = tmp_path / "b.txt"
        with pytest.raises(SystemExit):
            validate_paths([(m1, "file a"), (m2, "file b")])


# ---------------------------------------------------------------------------
# confirm
# ---------------------------------------------------------------------------


class TestConfirm:
    def test_yes_returns_true(self):
        with patch("builtins.input", return_value="y"):
            assert confirm("Continue?") is True

    def test_no_returns_false(self):
        with patch("builtins.input", return_value="n"):
            assert confirm("Continue?") is False

    def test_empty_with_default_true(self):
        with patch("builtins.input", return_value=""):
            assert confirm("Continue?", default=True) is True

    def test_empty_with_default_false(self):
        with patch("builtins.input", return_value=""):
            assert confirm("Continue?", default=False) is False

    def test_full_word_yes(self):
        with patch("builtins.input", return_value="yes"):
            assert confirm("Continue?") is True

    def test_full_word_no(self):
        with patch("builtins.input", return_value="no"):
            assert confirm("Continue?") is False


# ---------------------------------------------------------------------------
# get_thunderbird
# ---------------------------------------------------------------------------


class TestGetThunderbird:
    def test_bare_metal_found(self):
        with patch("invoice_toolkit.cli.utils.subprocess.run") as mock_run:
            mock_run.return_value = None
            result = get_thunderbird()
        assert result == ["thunderbird"]

    def test_flatpak_found(self):
        def side_effect(cmd, **kwargs):
            if cmd[0] == "thunderbird":
                raise FileNotFoundError

        with patch("invoice_toolkit.cli.utils.subprocess.run", side_effect=side_effect):
            result = get_thunderbird()
        assert result == ["flatpak", "run", "org.mozilla.Thunderbird"]

    def test_not_found(self):
        with patch("invoice_toolkit.cli.utils.subprocess.run", side_effect=FileNotFoundError):
            result = get_thunderbird()
        assert result is None


# ---------------------------------------------------------------------------
# compose_email
# ---------------------------------------------------------------------------


class TestComposeEmail:
    def test_basic_command_structure(self, tmp_path):
        pdf = tmp_path / "RE0001.pdf"
        xml = tmp_path / "RE0001.xml"
        pdf.touch()
        xml.touch()

        inv = make_invoice()
        cmd = compose_email(inv, make_config(), make_customer(), ["thunderbird"], pdf, xml, dry_run=False)
        assert cmd[0] == "thunderbird"
        assert cmd[1] == "-compose"
        assert "Rechnung RE0001" in cmd[2]

    def test_dry_run_prefix_in_subject(self, tmp_path):
        pdf = tmp_path / "RE0001.pdf"
        xml = tmp_path / "RE0001.xml"
        pdf.touch()
        xml.touch()

        inv = make_invoice()
        cmd = compose_email(inv, make_config(), make_customer(), ["thunderbird"], pdf, xml, dry_run=True)
        assert "DRY RUN:" in cmd[2]

    def test_missing_due_date_raises(self, tmp_path):
        pdf = tmp_path / "RE0001.pdf"
        xml = tmp_path / "RE0001.xml"
        pdf.touch()

        inv = make_invoice(due_date=None)
        with pytest.raises(ValueError, match="Due date must be set"):
            compose_email(inv, make_config(), make_customer(), ["thunderbird"], pdf, xml, dry_run=False)

    def test_pdf_attachment_included(self, tmp_path):
        pdf = tmp_path / "RE0001.pdf"
        xml = tmp_path / "RE0001.xml"
        pdf.touch()

        inv = make_invoice()
        cmd = compose_email(inv, make_config(), make_customer(), ["thunderbird"], pdf, xml, dry_run=False)
        assert str(pdf.absolute()) in cmd[2]

    def test_xml_attachment_when_exists(self, tmp_path):
        pdf = tmp_path / "RE0001.pdf"
        xml = tmp_path / "RE0001.xml"
        pdf.touch()
        xml.touch()

        inv = make_invoice()
        cmd = compose_email(inv, make_config(), make_customer(), ["thunderbird"], pdf, xml, dry_run=False)
        assert str(xml.absolute()) in cmd[2]

    def test_xml_attachment_excluded_when_missing(self, tmp_path):
        pdf = tmp_path / "RE0001.pdf"
        xml = tmp_path / "RE0001.xml"
        pdf.touch()
        # xml not created

        inv = make_invoice()
        cmd = compose_email(inv, make_config(), make_customer(), ["thunderbird"], pdf, xml, dry_run=False)
        assert str(xml.absolute()) not in cmd[2]

    def test_html_body_contains_customer_name(self, tmp_path):
        pdf = tmp_path / "RE0001.pdf"
        xml = tmp_path / "RE0001.xml"
        pdf.touch()

        inv = make_invoice()
        cmd = compose_email(inv, make_config(), make_customer(), ["thunderbird"], pdf, xml, dry_run=False)
        assert "Kunde Name" in cmd[2]
