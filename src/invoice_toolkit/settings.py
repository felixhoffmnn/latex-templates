"""Project path configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    """All directory/file paths needed by the toolkit.

    The caller (CLI or library user) provides all values — no defaults are assumed.
    """

    project_root: Path
    data_dir: Path
    out_dir: Path
    tmp_dir: Path
    template_dir: Path
    invoice_history_file: Path
    invoice_customer_file: Path
