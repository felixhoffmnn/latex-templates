"""Shared fixtures for the test suite."""

import os
from unittest.mock import patch

import pytest

_ENV_KEYS = ("INVOICES_PATH", "CONFIG_PATH", "LAST_INVOICE")


@pytest.fixture()
def env_cleanup():
    """Clear environment variables that influence path resolution and invoice IDs."""
    with patch.dict("os.environ"):
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        yield
